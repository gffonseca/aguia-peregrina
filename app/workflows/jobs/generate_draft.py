"""M6: gera minuta (sugestão) a partir de teses aprovadas + dossiê, com citações por página."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select

from app.core.audit import record
from app.core.db import SessionLocal
from app.core.tenancy import current_tenant_id
from app.llm import get_llm_client
from app.models.litigation import Case, Dossier, Draft, DraftCitation
from app.modules.m00_playbook.service import approved_theses, playbook_for_typology
from app.modules.m06_minuta.service import (
    DRAFT_PROMPT_VERSION,
    DraftOutput,
    humanize_refs,
    refs_in_body,
    system_prompt,
    user_prompt,
)
from app.workflows.jobs.build_dossier import case_summary, load_pages

log = logging.getLogger(__name__)

BLOCKING_ACTIONS = {"nao_gerar_minuta"}
PRELIMINARY_ONLY_ACTIONS = {"gerar_minuta_sem_merito"}


def _latest_dossier(db: Any, case_id: uuid.UUID, dossier_id: str | None) -> Dossier | None:
    if dossier_id:
        return db.get(Dossier, uuid.UUID(dossier_id))
    return db.scalar(
        select(Dossier)
        .where(Dossier.case_id == case_id, Dossier.status == "ready")
        .order_by(Dossier.version.desc())
        .limit(1)
    )


def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = uuid.UUID(payload["tenant_id"])
    case_id = uuid.UUID(payload["case_id"])
    draft_type = payload.get("draft_type", "contestacao")
    token = current_tenant_id.set(tenant_id)
    try:
        with SessionLocal() as db:
            case = db.get(Case, case_id)
            if case is None:
                return {"error": "case not found"}
            dossier = _latest_dossier(db, case_id, payload.get("dossier_id"))
            if dossier is None or dossier.status != "ready":
                return {"error": "dossiê pronto (M5) é pré-requisito da minuta"}
            content = dossier.content or {}
            actions = {
                a
                for x in content.get("exceptions_triggered", [])
                for a in [x.get("acao"), *x.get("acoes_paralelas", [])]
            }
            if actions & BLOCKING_ACTIONS:
                return {
                    "error": "playbook: exceção determina não gerar minuta",
                    "exceptions": content.get("exceptions_triggered"),
                }
            if content.get("missing_blocking_fields"):
                return {
                    "error": "campos bloqueantes do dossiê ausentes",
                    "missing": content["missing_blocking_fields"],
                }
            applicable = {t["code"] for t in content.get("applicable_theses", [])}
            theses_rows = approved_theses(db, case_typology=case.typology)
            theses = []
            for thesis, version in theses_rows:
                if thesis.code not in applicable:
                    continue
                cat = (version.conditions or {}).get("categoria")
                if cat == "sinal":
                    continue  # sinais são para o revisor, não argumentos da peça
                if actions & PRELIMINARY_ONLY_ACTIONS and cat not in {"preliminar", "processual"}:
                    continue
                theses.append(
                    {
                        "code": thesis.code,
                        "title": thesis.title,
                        "categoria": cat,
                        "version": version.version,
                        "version_id": str(version.id),
                        "approved_by_oab": version.approved_by_oab,
                        "body_markdown": version.body_markdown,
                    }
                )
            if not theses:
                return {
                    "error": "nenhuma tese aprovada aplicável ao caso",
                    "applicable": sorted(applicable),
                }
            pb = playbook_for_typology(case.typology)
            pages = load_pages(db, case_id)
            index = content.get("page_index") or {}
            llm = get_llm_client()
            messages = [
                {"role": "system", "content": system_prompt(draft_type)},
                {
                    "role": "user",
                    "content": user_prompt(
                        case_summary=case_summary(db, case),
                        dossier_content=content,
                        theses=theses,
                        pb=pb,
                        pages=pages,
                        operator_context=payload.get("context") or "",
                    ),
                },
            ]
            try:
                out, resp = llm.structured(
                    messages,
                    DraftOutput,
                    purpose="draft",
                    db=db,
                    tenant_id=tenant_id,
                    case_id=case_id,
                    prompt_version=DRAFT_PROMPT_VERSION,
                    temperature=0.2,
                    max_retries=0,  # uma tentativa: a chamada leva minutos; falha fica logada
                )
            except ValueError as exc:
                log.warning("minuta: saída estruturada inválida (%s)", exc)
                db.commit()
                return {"error": f"minuta não gerada: {exc}"}
            call_id = resp.llm_call_id
            alerts = list(out.reviewer_alerts)
            for x in content.get("exceptions_triggered", []):
                alerts.append(f"{x['id']} ({x['acao']}): {x['descricao']}")
            for sig in content.get("applicable_theses", []):
                if sig["code"] not in {t["code"] for t in theses} and sig["code"].startswith("T10"):
                    alerts.append(f"sinal {sig['code']}: {sig['nome']}")
            body = humanize_refs(out.body_markdown, index)
            if alerts or out.open_questions:
                head = ["> **ALERTAS AO REVISOR (não integram a peça)**"]
                head += [f"> - {a}" for a in alerts]
                head += [f"> - Pergunta em aberto: {q}" for q in out.open_questions]
                body = "\n".join(head) + "\n\n" + body
            last = db.scalar(
                select(Draft.version)
                .where(Draft.case_id == case_id, Draft.draft_type == draft_type)
                .order_by(Draft.version.desc())
                .limit(1)
            )
            draft = Draft(
                tenant_id=tenant_id,
                case_id=case_id,
                dossier_id=dossier.id,
                draft_type=draft_type,
                version=(last or 0) + 1,
                body_markdown=body,
                thesis_version_ids=[t["version_id"] for t in theses],
                confidence=out.confidence,
                llm_call_id=call_id,
            )
            db.add(draft)
            db.flush()
            kept, dropped = 0, 0
            seen: set[tuple[str, str]] = set()
            for c in out.citations:
                meta = index.get(c.page_ref)
                if meta is None:
                    dropped += 1
                    continue
                key = (c.page_ref, c.anchor[:120])
                if key in seen:
                    continue
                seen.add(key)
                db.add(
                    DraftCitation(
                        tenant_id=tenant_id,
                        draft_id=draft.id,
                        document_page_id=uuid.UUID(meta["document_page_id"]),
                        quote=c.quote,
                        anchor=c.anchor[:120],
                        evidence_score=c.evidence_score,
                    )
                )
                kept += 1
            unresolved = [r for r in refs_in_body(out.body_markdown) if r not in index]
            record(
                db,
                tenant_id=tenant_id,
                actor_user_id=None,
                actor_oab=None,
                action="draft.generate",
                entity_type="draft",
                entity_id=draft.id,
                payload={
                    "case_id": str(case_id),
                    "dossier_id": str(dossier.id),
                    "theses": [t["code"] for t in theses],
                    "citations": kept,
                    "citations_dropped": dropped,
                    "unresolved_refs": unresolved,
                    "llm_call_id": str(call_id) if call_id else None,
                },
            )
            db.commit()
            return {
                "draft_id": str(draft.id),
                "status": draft.status,
                "theses": [t["code"] for t in theses],
                "citations": kept,
                "citations_dropped": dropped,
                "unresolved_refs": unresolved,
                "confidence": out.confidence,
            }
    finally:
        current_tenant_id.reset(token)
