"""Integração Legal One: CNJ, cliente (token/paginação/retry) e sync idempotente.

Fixtures JSON em tests/fixtures/legalone são inventadas (sem dados reais)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy import func, select

from app.core import cnj
from app.integrations.legalone.client import (
    LegalOneClient,
    LegalOneError,
    LegalOneUnavailable,
)
from app.integrations.legalone.sync import (
    PROVIDER_UPDATE,
    LegalOneSync,
    derive_typology_hint,
)
from app.models.integrations import LegalOneRecord, LegalOneSyncRun
from app.models.litigation import Case, CaseParty, Client, Publication

FIXTURES = Path(__file__).parent / "fixtures" / "legalone"
BASE = "https://api.example.invalid/legalone/v1/api/rest"
OAUTH = "https://api.example.invalid/legalone/oauth"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeLegalOne:
    """Servidor falso em cima de httpx.MockTransport com o comportamento observado da API."""

    def __init__(self) -> None:
        self.token_calls = 0
        self.requests: list[tuple[str, dict[str, str]]] = []
        self.valid_tokens: set[str] = set()
        self.fail_503_times = 0
        self.expires_in = 1799

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        url = urlparse(str(request.url))
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        if str(request.url).startswith(OAUTH):
            self.token_calls += 1
            if not request.headers.get("Authorization", "").startswith("Basic "):
                return httpx.Response(401, json={"error": "invalid_client"})
            tok = f"tok-{self.token_calls}"
            self.valid_tokens.add(tok)
            body = {**_load("token.json"), "access_token": tok, "expires_in": self.expires_in}
            return httpx.Response(200, json=body)

        resource = url.path.rsplit("/rest/", 1)[-1]
        self.requests.append((resource, q))
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] not in self.valid_tokens:
            return httpx.Response(401, json={"message": "Unauthorized"})
        if self.fail_503_times > 0:
            self.fail_503_times -= 1
            return httpx.Response(503, text="Service Unavailable")
        top = int(q.get("$top", "30"))
        if top > 30:
            return httpx.Response(400, json={"error": {"message": "$top must be <= 30"}})
        skip = int(q.get("$skip", "0"))

        if resource == "lawsuits":
            if "updates" in q.get("$expand", ""):
                return httpx.Response(400, json={"error": {"message": "invalid $expand"}})
            items = _load("lawsuits_p1.json")["value"] + _load("lawsuits_p2.json")["value"]
            return httpx.Response(200, json={"value": items[skip : skip + top]})
        if resource == "contacts":
            items = _load("contacts.json")["value"]
            flt = q.get("$filter", "")
            if flt:
                ids = {int(p.split()[-1]) for p in flt.split(" or ")}
                items = [c for c in items if c["id"] in ids]
            return httpx.Response(200, json={"value": items[skip : skip + top]})
        if resource in ("updates", "tasks"):
            items = _load(f"{resource}.json")["value"]
            return httpx.Response(200, json={"value": items[skip : skip + top]})
        if resource == "appointments":
            return httpx.Response(200, json={"value": []})
        return httpx.Response(404, json={"message": "Resource not found"})


@pytest.fixture
def fake() -> FakeLegalOne:
    return FakeLegalOne()


@pytest.fixture
def client(fake: FakeLegalOne) -> LegalOneClient:
    sleeps: list[float] = []
    clock = {"t": 1000.0}
    c = LegalOneClient(
        "cid",
        "secret",
        base=BASE,
        oauth_url=OAUTH,
        http=httpx.Client(transport=fake.transport()),
        max_retries=2,
        backoff_seconds=0.5,
        sleep=sleeps.append,
        clock=lambda: clock["t"],
    )
    c._test_sleeps = sleeps  # type: ignore[attr-defined]
    c._test_clock = clock  # type: ignore[attr-defined]
    return c


# ------------------------------------------------------------------------------- CNJ
def test_cnj_parse_decodes_court_segment_and_validates_digit() -> None:
    c = cnj.parse("0812182-73.2018.8.14.0006")
    assert c is not None
    assert (c.segment, c.segment_name, c.tribunal, c.origin) == (8, "estadual", 14, "0006")
    assert c.court == "TJPA" and c.uf == "PA" and c.is_valid
    assert cnj.parse("00004569020255080012") is not None
    assert cnj.parse("0000456-90.2025.5.08.0012").court == "TRT8"  # type: ignore[union-attr]
    assert cnj.parse("1002233-82.2024.4.01.3900").court == "TRF1"  # type: ignore[union-attr]
    assert cnj.normalize("07003210420268140006") == "0700321-04.2026.8.14.0006"
    assert cnj.parse("0000006-66.2026.8.14.0301").is_valid is False  # type: ignore[union-attr]
    assert cnj.parse("123") is None and cnj.parse(None) is None and cnj.normalize("abc") is None


def test_cnj_find_in_text_normalizes_and_dedups() -> None:
    text = (
        "Sentença no processo 0700321-04.2026.8.14.0006 e também 07003210420268140006; "
        "ver 0801234-79.2026.8.14.0301."
    )
    assert cnj.find_in_text(text) == ["0700321-04.2026.8.14.0006", "0801234-79.2026.8.14.0301"]
    assert cnj.find_in_text(None) == []


def test_typology_hint() -> None:
    assert derive_typology_hint(cnj_segment=5, client_name=None, title="qualquer") == "trabalhista"
    assert (
        derive_typology_hint(cnj_segment=8, client_name="X", title="Desconto RMC indevido")
        == "consignado"
    )
    assert derive_typology_hint(cnj_segment=8, client_name="Y", title="Atraso de voo") == "voo"
    assert (
        derive_typology_hint(cnj_segment=8, client_name="Equatorial Energia", title=None)
        == "energia"
    )
    assert derive_typology_hint(cnj_segment=8, client_name="Loja Z", title="Cobrança") is None


# ---------------------------------------------------------------------------- client
def test_token_is_cached_then_refreshed_on_401(client: LegalOneClient, fake: FakeLegalOne) -> None:
    client.get("lawsuits", {"$top": 1})
    client.get("lawsuits", {"$top": 1})
    assert fake.token_calls == 1
    # servidor revoga o token: 401 → descarta cache, renova e repete uma vez
    fake.valid_tokens.clear()
    data = client.get("lawsuits", {"$top": 1})
    assert fake.token_calls == 2 and len(data["value"]) == 1
    # expiração: expires_in − 120 s
    client._test_clock["t"] += 1799 - 120 + 1  # type: ignore[attr-defined]
    client.get("lawsuits", {"$top": 1})
    assert fake.token_calls == 3


def test_oauth_failure_is_not_cached(fake: FakeLegalOne) -> None:
    bad = LegalOneClient("", "", base=BASE, oauth_url=OAUTH, http=httpx.Client())
    assert not bad.configured
    with pytest.raises(LegalOneError):
        bad.get("lawsuits")
    assert bad._token is None


def test_iterate_paginates_with_skip_and_caps_top(
    client: LegalOneClient, fake: FakeLegalOne
) -> None:
    items = list(client.iterate("lawsuits", {"$expand": "participants"}, page_size=2))
    assert [i["id"] for i in items] == [9103, 9102, 9101]
    pages = [q for r, q in fake.requests if r == "lawsuits"]
    assert [(p["$top"], p["$skip"]) for p in pages] == [("2", "0"), ("2", "2")]
    assert all(p["$expand"] == "participants" for p in pages)
    # max_pages corta a paginação
    assert len(list(client.iterate("lawsuits", page_size=2, max_pages=1))) == 2
    with pytest.raises(ValueError):
        client.get("lawsuits", {"$top": 31})
    with pytest.raises(ValueError):
        list(client.iterate("lawsuits", page_size=31))
    with pytest.raises(LegalOneError) as exc:
        client.get("lawsuits", {"$top": 1, "$expand": "updates"})
    assert exc.value.status_code == 400


def test_retry_with_backoff_then_unavailable(client: LegalOneClient, fake: FakeLegalOne) -> None:
    fake.fail_503_times = 1
    assert client.get("updates", {"$top": 1})["value"]
    assert client._test_sleeps == [0.5]  # type: ignore[attr-defined]
    fake.fail_503_times = 10
    with pytest.raises(LegalOneUnavailable):
        client.get("updates", {"$top": 1})
    assert client._test_sleeps == [0.5, 0.5, 1.0]  # type: ignore[attr-defined]


def test_probe_reports_resources_and_lookup_404(client: LegalOneClient) -> None:
    out = client.probe()
    assert out["oauth"] == "ok"
    assert out["resources"]["lawsuits"]["status"] == "ok"
    assert "identifierNumber" in out["resources"]["lawsuits"]["fields"]
    assert out["lookups"]["courts"]["status"] == "erro 404"
    assert set(out["update_relation"]) >= {"lawsuitId", "relationships"}


# ------------------------------------------------------------------------------ sync
def _counts(db) -> dict[str, int]:  # type: ignore[no-untyped-def]
    return {
        m.__tablename__: db.scalar(select(func.count()).select_from(m))
        for m in (Case, CaseParty, Client, Publication, LegalOneRecord)
    }


def test_sync_maps_and_is_idempotent(db, two_tenants, as_tenant, client) -> None:  # type: ignore[no-untyped-def]
    a, b = two_tenants
    with as_tenant(a):
        first = LegalOneSync(db, tenant_id=a, client=client).run(max_pages=5)
        assert first["status"] == "ok"
        assert first["cases_created"] == 3 and first["clients_created"] == 3
        assert first["publications_created"] == 4 and first["updates_unlinked"] == 1
        assert first["link_strategies"] == {
            "relationships": 1,
            "lawsuitId": 1,
            "cnj_in_text": 1,
            "unlinked": 1,
            "task:cnj_in_text": 1,
            "task:relationships": 1,
        }
        snapshot = _counts(db)

        case = db.scalar(select(Case).where(Case.external_ref == "legalone:9103"))
        assert case is not None
        assert case.cnj_number == "0801234-79.2026.8.14.0301" and case.court == "TJPA"
        assert case.status == "active" and case.claim_value == 12500.5
        assert case.filed_at.isoformat() == "2026-10-02"
        assert case.typology_hint == "consignado"
        assert case.meta["legalone"]["folder"] == "2026/0453"
        assert case.meta["legalone"]["nature_id"] == 12 and case.meta["cnj"]["court"] == "TJPA"
        roles = {p.name: p.role for p in case.parties}
        assert roles == {
            "Banco Fictício Pagamentos S.A.": "cliente",
            "Joana Exemplo da Silva": "parte_contraria",
            "Advogado Modelo Teste": "advogado_contrario",
            "Associada Interna Exemplo": "responsavel_interno",
        }
        cli = db.get(Client, case.client_id)
        assert cli is not None and cli.erp_kind == "legalone"
        assert cli.document == "12345678000190"  # enriquecido por contacts
        assert cli.erp_config["legalone_contact_id"] == 501

        trab = db.scalar(select(Case).where(Case.external_ref == "legalone:9102"))
        assert trab is not None and trab.court == "TRT8" and trab.typology_hint == "trabalhista"

        closed = db.scalar(select(Case).where(Case.external_ref == "legalone:9101"))
        assert closed is not None and closed.status == "closed"
        assert closed.cnj_number == "0700321-04.2026.8.14.0006"  # normalizado de 20 dígitos
        assert closed.typology_hint == "voo" and closed.claim_value == 5000.0

        pubs = {p.provider_ref: p for p in db.scalars(select(Publication))}
        assert all(p.provider == PROVIDER_UPDATE for p in pubs.values())
        assert pubs["55001"].case_id == case.id
        assert pubs["55002"].case_id == trab.id
        assert pubs["55003"].case_id == closed.id and pubs["55003"].cnj_number == closed.cnj_number
        assert pubs["55004"].case_id is None
        assert (
            pubs["55002"].raw_text
            == "Audiência designada para 20/11/2026\n\nComparecer com preposto"
        )

        tasks = list(db.scalars(select(LegalOneRecord).where(LegalOneRecord.kind == "task")))
        assert {t.external_id: t.linked_id for t in tasks} == {"81001": case.id, "81002": trab.id}
        assert all(t.source_date is not None for t in tasks)

        runs = list(db.scalars(select(LegalOneSyncRun)))
        assert (
            len(runs) == 1
            and runs[0].status == "ok"
            and runs[0].cursor["lawsuits"] == {"max_id": 9103}
        )

        # segunda execução: nada duplicado, tudo atualizado
        second = LegalOneSync(db, tenant_id=a, client=client).run(max_pages=5)
        assert second["status"] == "ok"
        assert _counts(db) == snapshot
        assert second.get("cases_created", 0) == 0 and second["cases_updated"] == 3
        assert second.get("parties_created", 0) == 0 and second["parties_updated"] == 8
        assert second.get("publications_created", 0) == 0 and second["publications_updated"] == 4
        assert second.get("clients_created", 0) == 0
        sync3 = LegalOneSync(db, tenant_id=a, client=client)
        assert sync3.last_successful_since() is not None

    # muralha: o outro tenant não enxerga nada do sync
    with as_tenant(b):
        assert db.scalar(select(func.count()).select_from(Case)) == 0
        assert db.scalar(select(func.count()).select_from(LegalOneRecord)) == 0


def test_sync_adopts_manual_case_by_cnj_and_marks_errors(  # type: ignore[no-untyped-def]
    db, two_tenants, as_tenant, client, fake
) -> None:
    a, _ = two_tenants
    with as_tenant(a):
        manual = Case(cnj_number="0801234-79.2026.8.14.0301", typology="consignado")
        db.add(manual)
        db.commit()
        LegalOneSync(db, tenant_id=a, client=client).run(resources=("lawsuits",))
        again = db.scalar(select(Case).where(Case.cnj_number == "0801234-79.2026.8.14.0301"))
        assert again is not None and again.id == manual.id
        assert again.external_ref == "legalone:9103" and again.typology == "consignado"
        assert db.scalar(select(func.count()).select_from(Case)) == 3

        fake.fail_503_times = 99
        with pytest.raises(LegalOneUnavailable):
            LegalOneSync(db, tenant_id=a, client=client).run(resources=("updates",))
        last = db.scalar(select(LegalOneSyncRun).order_by(LegalOneSyncRun.started_at.desc()))
        assert last is not None and last.status == "error" and "503" in (last.error or "")


def test_since_filter_and_fallback_without_filter(  # type: ignore[no-untyped-def]
    db, two_tenants, as_tenant, client, fake
) -> None:
    from datetime import date

    a, _ = two_tenants
    with as_tenant(a):
        LegalOneSync(db, tenant_id=a, client=client).run(
            since=date(2026, 10, 1), max_pages=2, resources=("lawsuits", "updates", "tasks")
        )
    filters = {r: q.get("$filter") for r, q in fake.requests}
    assert filters["lawsuits"] == "creationDate ge 2026-10-01T00:00:00Z"
    assert filters["updates"] == "date ge 2026-10-01T00:00:00Z"
    assert filters["tasks"] == "deadLine ge 2026-10-01T00:00:00Z"
    orderby = {r: q.get("$orderby") for r, q in fake.requests}
    assert orderby["lawsuits"] == "id desc" and orderby["updates"] == "date desc"

    # API recusa o filtro (400) → refaz sem filtro, limitado a max_pages
    original = fake.handle

    def reject_filter(request: httpx.Request) -> httpx.Response:
        if "tasks" in str(request.url) and "%24filter" in str(request.url):
            return httpx.Response(400, json={"error": {"message": "deadLine is not filterable"}})
        return original(request)

    strict = LegalOneClient(
        "cid",
        "secret",
        base=BASE,
        oauth_url=OAUTH,
        http=httpx.Client(transport=httpx.MockTransport(reject_filter)),
        sleep=lambda _: None,
    )
    with as_tenant(a):
        res = LegalOneSync(db, tenant_id=a, client=strict).run(
            since=date(2026, 10, 1), resources=("tasks",)
        )
    assert res["tasks_filter_rejected"] == 1 and res["tasks_seen"] == 2


# ------------------------------------------------------------------------- job + API
def test_job_and_ops_endpoints(
    db, two_tenants, as_tenant, session_factory, client, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    import app.api.integrations as api_mod
    import app.workflows.jobs.sync_legalone as job_mod
    from app.core.config import get_settings
    from app.main import app

    a, _ = two_tenants
    monkeypatch.setattr(job_mod, "SessionLocal", session_factory)
    monkeypatch.setattr(job_mod, "get_legalone_client", lambda: client)
    monkeypatch.setattr(api_mod, "get_legalone_client", lambda: client)

    result = job_mod.run({"tenant_id": str(a), "since": "2026-10-01", "max_pages": 3})
    assert result["status"] == "ok" and result["since"] == "2026-10-01"
    result = job_mod.run({"tenant_id": str(a), "since": "auto", "resources": ["lawsuits"]})
    assert result["since"] is not None and result["cases_updated"] == 3

    settings = get_settings()
    http = TestClient(app)
    monkeypatch.setattr(settings, "ops_key", None)
    assert http.get("/integrations/legalone/probe").status_code == 404
    monkeypatch.setattr(settings, "ops_key", "ops-secret")
    assert http.get("/integrations/legalone/probe").status_code == 404  # sem header
    r = http.get("/integrations/legalone/probe", headers={"X-Ops-Key": "ops-secret"})
    assert r.status_code == 200 and r.json()["resources"]["lawsuits"]["status"] == "ok"

    hdrs = {"X-Ops-Key": "ops-secret", "X-Tenant-ID": str(a)}
    assert http.post("/integrations/legalone/sync", json={}).status_code == 400  # sem tenant
    r = http.post("/integrations/legalone/sync", json={"resources": ["x"]}, headers=hdrs)
    assert r.status_code == 422
    r = http.post(
        "/integrations/legalone/sync",
        json={"since": None, "max_pages": 2, "resources": ["lawsuits", "updates"]},
        headers=hdrs,
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["job"] == "sync_legalone" and body["engine"] == "in_process"
    assert body["result"]["status"] == "ok" and body["result"]["cases_updated"] == 3


def test_cli_parser_builds_payload() -> None:
    from app.workflows.run import build_parser

    ns = build_parser().parse_args(
        [
            "sync_legalone",
            "--since",
            "2026-10-01",
            "--max-pages",
            "50",
            "--tenant-id",
            str(uuid.uuid4()),
        ]
    )
    assert ns.job == "sync_legalone" and ns.max_pages == 50 and ns.since == "2026-10-01"
