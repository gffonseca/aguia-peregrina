"""Sync incremental Legal One → plataforma.

Mapeamento:
- `lawsuits` (+`$expand=participants`) → `cases` (`external_ref = "legalone:<id>"`, número CNJ
  normalizado, pasta, título, status, valores, datas; ids de lookup no `meta`) e
  `case_parties` (Customer→cliente, OtherParty→parte_contraria,
  LawyerOfOtherParty→advogado_contrario, PersonInCharge→responsavel_interno).
- `contacts` dos participantes Customer → `clients` (`erp_kind = "legalone"`).
- `updates` → `publications` (`provider = "legalone_update"`).
- `tasks` → `legalone_records` (kind `task`): ainda não há tabela de prazos; ver README.
- Tudo que é lido fica em `legalone_records` (JSON bruto) para reprocessamento.

Cursor: `since` filtra `creationDate` (lawsuits) / `date` (updates) / `deadLine` (tasks);
ordenação `id desc` / `date desc`. Upserts idempotentes por id externo. A relação
update→lawsuit não é documentada pela API: tentamos `lawsuitId`/`litigationId`,
`relationships[]` e, por fim, número CNJ no texto (`strategy` nas estatísticas).
"""

from __future__ import annotations

import logging
import re
import uuid
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import cnj as cnjlib
from app.integrations.legalone.client import LegalOneClient, LegalOneError
from app.models.integrations import LegalOneRecord, LegalOneSyncRun
from app.models.litigation import Case, CaseParty, Client, Publication

log = logging.getLogger(__name__)

PROVIDER_UPDATE = "legalone_update"
EXTERNAL_REF_PREFIX = "legalone:"
DEFAULT_RESOURCES: tuple[str, ...] = ("lawsuits", "contacts", "updates", "tasks")

ROLE_MAP: dict[str, str] = {
    "Customer": "cliente",
    "OtherParty": "parte_contraria",
    "LawyerOfOtherParty": "advogado_contrario",
    "PersonInCharge": "responsavel_interno",
    "Party": "parte",
    "Other": "terceiro",
}

# (tipologia, palavras-chave) — avaliadas em ordem; a primeira que casar vence
TITLE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "consignado",
        ("consignado", "rmc", "rcc", "cartão", "cartao", "empréstimo", "emprestimo", "inss"),
    ),
    ("energia", ("energia", "equatorial", "celpa", "medidor", "fatura de energia", "toi")),
    ("voo", ("voo", "vôo", "aérea", "aerea", "bagagem", "overbooking", "latam", "azul", "gol ")),
    ("trabalhista", ("reclamatória", "reclamatoria", "trabalhista", "rescisórias", "rescisorias")),
    ("telecom", ("telefonia", "linha telefônica", "linha telefonica", "internet", "cobrança tim")),
    ("plano_saude", ("plano de saúde", "plano de saude", "unimed", "hapvida")),
)
CLIENT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("energia", ("energia", "equatorial", "celpa", "eletro")),
    ("voo", ("linhas aéreas", "linhas aereas", "airlines", "latam", "azul", "gol ")),
    ("consignado", ("banco", "financeira", "crédito", "credito", "pagamentos", "bmg", "pan ")),
    ("telecom", ("telecom", "telefonia", "claro", "vivo", "tim ")),
)


def derive_typology_hint(
    *, cnj_segment: int | None, client_name: str | None, title: str | None
) -> str | None:
    """Palpite determinístico; a tipologia final é da classificação do M1."""
    if cnj_segment == 5:
        return "trabalhista"
    t = f" {(title or '').lower()} "
    for typology, words in TITLE_KEYWORDS:
        if any(w in t for w in words):
            return typology
    c = f" {(client_name or '').lower()} "
    for typology, words in CLIENT_KEYWORDS:
        if any(w in c for w in words):
            return typology
    return None


# --------------------------------------------------------------------------- utils
_ISO_TZ = re.compile(r"(Z|[+-]\d{2}:?\d{2})$")


def parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            dt = datetime.fromisoformat(s[:19])
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def parse_date(value: Any) -> date | None:
    dt = parse_datetime(value)
    return dt.date() if dt else None


def _odata_dt(d: date) -> str:
    return f"{d.isoformat()}T00:00:00Z"


def _money(item: dict[str, Any]) -> float | None:
    m = item.get("monetaryAmount")
    if isinstance(m, dict) and m.get("value") is not None:
        try:
            return float(m["value"])
        except (TypeError, ValueError):
            pass
    for key in ("involvedAmount", "amountOfSettlementOrJudgment"):
        v = item.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def _digits(value: Any) -> str | None:
    if value is None:
        return None
    d = re.sub(r"\D", "", str(value))
    return d[:20] or None


@dataclass
class SyncStats:
    counters: Counter[str] = field(default_factory=Counter)
    link_strategies: Counter[str] = field(default_factory=Counter)
    errors: list[str] = field(default_factory=list)

    def inc(self, key: str, n: int = 1) -> None:
        self.counters[key] += n

    def as_dict(self) -> dict[str, Any]:
        return {
            **dict(sorted(self.counters.items())),
            "link_strategies": dict(self.link_strategies),
            "errors": self.errors[:50],
        }


class LegalOneSync:
    def __init__(
        self,
        db: Session,
        *,
        tenant_id: uuid.UUID,
        client: LegalOneClient,
        now: datetime | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.client = client
        self.now = now or datetime.now(UTC)
        self.stats = SyncStats()
        self._pending_contact_ids: set[str] = set()
        self._clients_by_contact: dict[str, Client] | None = None

    # ------------------------------------------------------------------ public
    def last_successful_since(self) -> date | None:
        """Data de início da última execução bem-sucedida (para `since="auto"`)."""
        run = self.db.scalar(
            select(LegalOneSyncRun)
            .where(LegalOneSyncRun.status == "ok")
            .order_by(LegalOneSyncRun.started_at.desc())
            .limit(1)
        )
        return run.started_at.date() if run else None

    def run(
        self,
        *,
        since: date | None = None,
        max_pages: int | None = None,
        resources: Iterable[str] = DEFAULT_RESOURCES,
    ) -> dict[str, Any]:
        resources = tuple(resources)
        sync_run = LegalOneSyncRun(
            tenant_id=self.tenant_id,
            started_at=self.now,
            since=since,
            resources=list(resources),
            status="running",
        )
        self.db.add(sync_run)
        self.db.commit()
        cursor: dict[str, Any] = {"since": since.isoformat() if since else None}
        try:
            if "lawsuits" in resources:
                cursor["lawsuits"] = self.sync_lawsuits(since=since, max_pages=max_pages)
                self.db.commit()
            if "contacts" in resources:
                cursor["contacts"] = self.sync_contacts()
                self.db.commit()
            if "updates" in resources:
                cursor["updates"] = self.sync_updates(since=since, max_pages=max_pages)
                self.db.commit()
            if "tasks" in resources:
                cursor["tasks"] = self.sync_tasks(since=since, max_pages=max_pages)
                self.db.commit()
            sync_run.status = "ok"
        except Exception as exc:
            self.db.rollback()
            sync_run.status = "error"
            sync_run.error = f"{type(exc).__name__}: {exc}"[:2000]
            self.stats.errors.append(sync_run.error)
            raise
        finally:
            sync_run.finished_at = datetime.now(UTC)
            sync_run.stats = self.stats.as_dict()
            sync_run.cursor = cursor
            self.db.add(sync_run)
            self.db.commit()
        return {"run_id": str(sync_run.id), "status": sync_run.status, **self.stats.as_dict()}

    # ---------------------------------------------------------------- lawsuits
    def sync_lawsuits(self, *, since: date | None, max_pages: int | None) -> dict[str, Any]:
        params: dict[str, Any] = {"$expand": "participants", "$orderby": "id desc"}
        flt = f"creationDate ge {_odata_dt(since)}" if since else None
        max_id = 0
        for item in self._iterate_with_fallback("lawsuits", params, flt, max_pages):
            try:
                case = self.upsert_lawsuit(item)
                max_id = max(max_id, int(item.get("id") or 0))
                self.stats.inc("lawsuits_seen")
                log.debug("legalone lawsuit %s → case %s", item.get("id"), case.id)
            except Exception as exc:  # um registro ruim não derruba a página inteira
                self.stats.inc("lawsuits_failed")
                self.stats.errors.append(f"lawsuit {item.get('id')}: {exc}")
                log.exception("legalone: falha no lawsuit %s", item.get("id"))
        return {"max_id": max_id}

    def upsert_lawsuit(self, item: dict[str, Any]) -> Case:
        ext_id = str(item["id"])
        external_ref = f"{EXTERNAL_REF_PREFIX}{ext_id}"
        identifier = item.get("identifierNumber")
        cnj = cnjlib.parse(identifier)
        if cnj:
            cnj_number = cnj.formatted
        else:
            cnj_number = (str(identifier).strip() if identifier else external_ref)[:25]

        case = self.db.scalar(select(Case).where(Case.external_ref == external_ref))
        created = False
        if case is None and cnj is not None:
            # caso criado à mão (ou por publicação) antes do sync: adota pelo CNJ
            case = self.db.scalar(
                select(Case).where(Case.cnj_number == cnj_number, Case.external_ref.is_(None))
            )
        if case is None:
            case = Case(tenant_id=self.tenant_id, cnj_number=cnj_number, external_ref=external_ref)
            self.db.add(case)
            created = True

        case.external_ref = external_ref
        case.cnj_number = cnj_number
        if cnj:
            case.court = cnj.court
        case.claim_value = _money(item)
        case.filed_at = parse_date(item.get("distributionDate")) or case.filed_at
        case.status = "closed" if item.get("closed") else "active"

        participants = item.get("participants") or []
        client_name = self._sync_participants(case, participants)

        legal_meta = {
            "id": item.get("id"),
            "folder": item.get("folder"),
            "title": item.get("title"),
            "type": item.get("type"),
            "identifier_number": identifier,
            "status_id": item.get("statusId"),
            "closed": bool(item.get("closed")),
            "distribution_date": item.get("distributionDate"),
            "termination_date": item.get("terminationDate"),
            "closing_date": item.get("closingDate"),
            "creation_date": item.get("creationDate"),
            "responsible_office_id": item.get("responsibleOfficeId"),
            "origin_office_id": item.get("originOfficeId"),
            "nature_id": item.get("natureId"),
            "action_type_id": item.get("actionTypeId"),
            "phase_id": item.get("phaseId"),
            "court_id": item.get("courtId"),
            "justice_id": item.get("justiceId"),
            "level_id": item.get("levelId"),
            "jurisdiction_id": item.get("jurisdictionId"),
            "state_id": item.get("stateId"),
            "city_id": item.get("cityId"),
            "costs_type": item.get("costsType"),
            "probability": item.get("probability"),
            "probability_type": item.get("probabilityType"),
            "monetary_amount": item.get("monetaryAmount"),
            "involved_amount": item.get("involvedAmount"),
            "amount_of_settlement_or_judgment": item.get("amountOfSettlementOrJudgment"),
            "court_panel": item.get("courtPanel"),
            "synced_at": self.now.isoformat(),
        }
        case.meta = {
            **(case.meta or {}),
            "source": "legalone",
            "legalone": legal_meta,
            "cnj": cnj.as_dict() if cnj else None,
        }
        case.typology_hint = derive_typology_hint(
            cnj_segment=cnj.segment if cnj else None,
            client_name=client_name,
            title=item.get("title"),
        )
        self.db.flush()
        self._upsert_raw(
            "lawsuit",
            ext_id,
            item,
            source_date=parse_datetime(item.get("creationDate")),
            linked=("case", case.id),
        )
        self.stats.inc("cases_created" if created else "cases_updated")
        return case

    def _sync_participants(self, case: Case, participants: list[dict[str, Any]]) -> str | None:
        """Upsert de `case_parties`; devolve o nome do cliente (Customer principal)."""
        existing = {
            self._party_key(p.meta): p
            for p in self.db.scalars(select(CaseParty).where(CaseParty.case_id == case.id))
            if p.meta and p.meta.get("legalone_participant_key")
        }
        client_name: str | None = None
        client_set = False
        for p in participants:
            if not isinstance(p, dict):
                continue
            ptype = str(p.get("type") or "Other")
            contact_id = p.get("contactId")
            key = f"{ptype}:{contact_id if contact_id is not None else p.get('id')}"
            name = (p.get("contactName") or f"contato {contact_id}")[:300]
            meta = {
                "legalone_participant_key": key,
                "legalone_participant_id": p.get("id"),
                "legalone_contact_id": contact_id,
                "legalone_type": ptype,
                "position_id": p.get("positionId"),
                "is_main": bool(p.get("isMainParticipant")),
            }
            party = existing.get(key)
            if party is None:
                party = CaseParty(
                    tenant_id=self.tenant_id,
                    case_id=case.id,
                    role=ROLE_MAP.get(ptype, "terceiro"),
                    name=name,
                    meta=meta,
                )
                self.db.add(party)
                existing[key] = party
                self.stats.inc("parties_created")
            else:
                party.role = ROLE_MAP.get(ptype, "terceiro")
                party.name = name
                party.meta = {**party.meta, **meta}
                self.stats.inc("parties_updated")

            if ptype == "Customer":
                client = self._ensure_client(contact_id, name)
                if client is not None and (not client_set or p.get("isMainParticipant")):
                    case.client_id = client.id
                    client_name = client.name
                    client_set = True
                if contact_id is not None:
                    self._pending_contact_ids.add(str(contact_id))
        return client_name

    @staticmethod
    def _party_key(meta: dict[str, Any] | None) -> str:
        return str((meta or {}).get("legalone_participant_key"))

    # ----------------------------------------------------------------- clients
    def _load_clients(self) -> dict[str, Client]:
        if self._clients_by_contact is None:
            self._clients_by_contact = {}
            for c in self.db.scalars(select(Client).where(Client.erp_kind == "legalone")):
                cid = (c.erp_config or {}).get("legalone_contact_id")
                if cid is not None:
                    self._clients_by_contact[str(cid)] = c
        return self._clients_by_contact

    def _ensure_client(self, contact_id: Any, name: str) -> Client | None:
        clients = self._load_clients()
        if contact_id is not None and str(contact_id) in clients:
            return clients[str(contact_id)]
        # cliente já cadastrado à mão com o mesmo nome? vincula em vez de duplicar
        client = self.db.scalar(select(Client).where(Client.name == name[:200]).limit(1))
        if client is None:
            client = Client(tenant_id=self.tenant_id, name=name[:200], erp_kind="legalone")
            self.db.add(client)
            self.stats.inc("clients_created")
        if contact_id is not None:
            client.erp_kind = "legalone"
            client.erp_config = {**(client.erp_config or {}), "legalone_contact_id": contact_id}
            self.db.flush()
            clients[str(contact_id)] = client
        return client

    def sync_contacts(self, contact_ids: Iterable[str] | None = None) -> dict[str, Any]:
        """Enriquece `clients` (documento, nome oficial) com `contacts` dos ids pendentes.

        Busca por `$filter=id eq a or id eq b …` em lotes de 10 (o operador `in` não foi
        verificado no tenant).
        """
        ids = sorted(set(contact_ids) if contact_ids is not None else self._pending_contact_ids)
        if not ids:
            return {"fetched": 0}
        clients = self._load_clients()
        fetched = 0
        for i in range(0, len(ids), 10):
            batch = ids[i : i + 10]
            flt = " or ".join(f"id eq {int(x)}" for x in batch if x.isdigit())
            if not flt:
                continue
            for item in self.client.iterate("contacts", {"$filter": flt}, max_pages=1):
                fetched += 1
                ext_id = str(item.get("id"))
                client = clients.get(ext_id)
                if client is not None:
                    if item.get("name"):
                        client.name = str(item["name"])[:200]
                    doc = _digits(item.get("identificationNumber"))
                    if doc:
                        client.document = doc
                    client.erp_config = {
                        **(client.erp_config or {}),
                        "legalone_contact_id": item.get("id"),
                        "legalone_contact_type": item.get("type"),
                    }
                    self.stats.inc("clients_enriched")
                self._upsert_raw(
                    "contact",
                    ext_id,
                    item,
                    source_date=parse_datetime(item.get("creationDate")),
                    linked=("client", client.id) if client else None,
                )
        self._pending_contact_ids.clear()
        return {"fetched": fetched}

    # ----------------------------------------------------------------- updates
    def sync_updates(self, *, since: date | None, max_pages: int | None) -> dict[str, Any]:
        params: dict[str, Any] = {"$orderby": "date desc"}
        flt = f"date ge {_odata_dt(since)}" if since else None
        max_date: datetime | None = None
        for item in self._iterate_with_fallback("updates", params, flt, max_pages):
            try:
                pub = self.upsert_update(item)
                self.stats.inc("updates_seen")
                if pub.published_at and (max_date is None or pub.published_at > max_date):
                    max_date = pub.published_at
            except Exception as exc:
                self.stats.inc("updates_failed")
                self.stats.errors.append(f"update {item.get('id')}: {exc}")
                log.exception("legalone: falha no update %s", item.get("id"))
        return {"max_date": max_date.isoformat() if max_date else None}

    def upsert_update(self, item: dict[str, Any]) -> Publication:
        ext_id = str(item["id"])
        case, strategy = self.resolve_case(item)
        self.stats.link_strategies[strategy] += 1
        text_parts = [str(item.get("description") or "").strip()]
        if item.get("notes"):
            text_parts.append(str(item["notes"]).strip())
        raw_text = "\n\n".join(p for p in text_parts if p) or None
        cnj_in_text = cnjlib.find_in_text(raw_text)
        pub = self.db.scalar(
            select(Publication).where(
                Publication.provider == PROVIDER_UPDATE, Publication.provider_ref == ext_id
            )
        )
        created = pub is None
        if pub is None:
            pub = Publication(
                tenant_id=self.tenant_id, provider=PROVIDER_UPDATE, provider_ref=ext_id
            )
            self.db.add(pub)
        pub.case_id = case.id if case else pub.case_id
        pub.cnj_number = case.cnj_number if case else (cnj_in_text[0] if cnj_in_text else None)
        pub.published_at = parse_datetime(item.get("date")) or parse_datetime(
            item.get("creationDate")
        )
        pub.raw_text = raw_text
        pub.category = pub.category or "andamento"
        self.db.flush()
        self._upsert_raw(
            "update",
            ext_id,
            item,
            source_date=pub.published_at,
            linked=("publication", pub.id),
        )
        self.stats.inc("publications_created" if created else "publications_updated")
        if case is None:
            self.stats.inc("updates_unlinked")
        return pub

    # ------------------------------------------------------------------- tasks
    def sync_tasks(self, *, since: date | None, max_pages: int | None) -> dict[str, Any]:
        """Sem tabela de prazos ainda: guarda em `legalone_records` (kind=task) com vínculo
        ao caso quando descoberto. `deadLine` filtrável não foi verificado → fallback."""
        params: dict[str, Any] = {"$orderby": "deadLine desc"}
        flt = f"deadLine ge {_odata_dt(since)}" if since else None
        n = 0
        for item in self._iterate_with_fallback("tasks", params, flt, max_pages):
            ext_id = str(item.get("id"))
            case, strategy = self.resolve_case(item)
            self.stats.link_strategies[f"task:{strategy}"] += 1
            self._upsert_raw(
                "task",
                ext_id,
                item,
                source_date=parse_datetime(item.get("deadLine"))
                or parse_datetime(item.get("endDateTime")),
                linked=("case", case.id) if case else None,
            )
            n += 1
        self.stats.inc("tasks_seen", n)
        return {"seen": n}

    # ------------------------------------------------------------------ linking
    def resolve_case(self, item: dict[str, Any]) -> tuple[Case | None, str]:
        """Descobre o processo de um update/task. Estratégias em ordem de confiança."""
        for key in ("lawsuitId", "litigationId", "lawsuit_id"):
            if item.get(key):
                case = self._case_by_ext(item[key])
                if case:
                    return case, key
        rels = item.get("relationships") or item.get("relationShips") or []
        if isinstance(rels, list):
            for r in rels:
                if not isinstance(r, dict):
                    continue
                link_type = str(r.get("linkType") or r.get("type") or "").lower()
                link_id = r.get("linkId") or r.get("id")
                if link_id and link_type in ("", "litigation", "lawsuit"):
                    case = self._case_by_ext(link_id)
                    if case:
                        return case, "relationships"
        text = " ".join(str(item.get(k) or "") for k in ("description", "notes", "title"))
        for number in cnjlib.find_in_text(text):
            case = self.db.scalar(select(Case).where(Case.cnj_number == number))
            if case:
                return case, "cnj_in_text"
        return None, "unlinked"

    def _case_by_ext(self, ext_id: Any) -> Case | None:
        return self.db.scalar(
            select(Case).where(Case.external_ref == f"{EXTERNAL_REF_PREFIX}{ext_id}")
        )

    # --------------------------------------------------------------------- raw
    def _upsert_raw(
        self,
        kind: str,
        external_id: str,
        payload: dict[str, Any],
        *,
        source_date: datetime | None,
        linked: tuple[str, uuid.UUID] | None,
    ) -> LegalOneRecord:
        rec = self.db.scalar(
            select(LegalOneRecord).where(
                LegalOneRecord.kind == kind, LegalOneRecord.external_id == external_id
            )
        )
        if rec is None:
            rec = LegalOneRecord(tenant_id=self.tenant_id, kind=kind, external_id=external_id)
            self.db.add(rec)
            self.stats.inc(f"raw_{kind}_created")
        else:
            self.stats.inc(f"raw_{kind}_updated")
        rec.payload = payload
        rec.source_date = source_date
        rec.fetched_at = self.now
        if linked:
            rec.linked_entity, rec.linked_id = linked
        self.db.flush()
        return rec

    # ----------------------------------------------------------------- paging
    def _iterate_with_fallback(
        self,
        resource: str,
        params: dict[str, Any],
        flt: str | None,
        max_pages: int | None,
    ) -> Iterator[dict[str, Any]]:
        """Tenta com `$filter`; se a API recusar (400) o filtro/ordenação, refaz sem eles
        respeitando `max_pages` (e registra nas estatísticas)."""
        full = {**params, "$filter": flt} if flt else dict(params)
        try:
            yield from self.client.iterate(resource, full, max_pages=max_pages)
            return
        except LegalOneError as exc:
            if exc.status_code != 400 or (not flt and "$orderby" not in params):
                raise
            self.stats.inc(f"{resource}_filter_rejected")
            log.warning("legalone: %s recusou filtro/ordenação (%s); sem filtro", resource, exc)
        fallback = {k: v for k, v in params.items() if k != "$orderby"}
        yield from self.client.iterate(resource, fallback, max_pages=max_pages or 1)


__all__ = [
    "DEFAULT_RESOURCES",
    "EXTERNAL_REF_PREFIX",
    "PROVIDER_UPDATE",
    "ROLE_MAP",
    "LegalOneSync",
    "SyncStats",
    "derive_typology_hint",
    "parse_date",
    "parse_datetime",
]
