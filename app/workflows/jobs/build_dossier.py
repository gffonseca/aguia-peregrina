"""M5: consolida páginas + subsídios + antifraude em um dossiê estruturado e avalia o playbook."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.db import SessionLocal
from app.core.tenancy import current_tenant_id
from app.llm import get_llm_client
from app.models.litigation import Case, CaseParty, Document, DocumentPage, Dossier, FraudCheck
from app.modules.m00_playbook.service import playbook_for_typology
from app.modules.m03_subsidios.service import get_subsidies
from app.modules.m05_dossie.service import (
    DOSSIER_PROMPT_VERSION,
    DossierExtraction,
    build_page_index,
    evaluate_playbook,
    merge_fields,
    resolve_refs,
    system_prompt,
    user_prompt,
)

log = logging.getLogger(__name__)


def load_pages(db: Session, case_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = db.execute(
        select(DocumentPage, Document)
        .join(Document, Document.id == DocumentPage.document_id)
        .where(Document.case_id == case_id)
        .order_by(Document.created_at, DocumentPage.page_number)
    ).all()
    return [
        {
            "document_page_id": page.id,
            "document_id": doc.id,
            "filename": doc.filename,
            "page_number": page.page_number,
            "page_type": page.page_type,
            "text": page.text or "",
        }
        for page, doc in rows
    ]


def case_summary(db: Session, case: Case) -> dict[str, Any]:
    parties = list(db.scalars(select(CaseParty).where(CaseParty.case_id == case.id)))
    return {
        "cnj_number": case.cnj_number,
        "court": case.court,
        "comarca": case.comarca,
        "vara": case.vara,
        "typology": case.typology,
        "phase": case.phase,
        "claim_value": case.claim_value,
        "filed_at": case.filed_at,
        "parties": [
            {"role": p.role, "name": p.name, "document": p.document, "oab": p.oab} for p in parties
        ],
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = uuid.UUID(payload["tenant_id"])
    case_id = uuid.UUID(payload["case_id"])
    token = current_tenant_id.set(tenant_id)
    try:
        with SessionLocal() as db:
            case = db.get(Case, case_id)
            if case is None:
                return {"error": "case not found"}
            pages = load_pages(db, case_id)
            if not pages:
                return {"error": "processo sem páginas processadas (M2)"}
            index = build_page_index(pages)
            subsidies = get_subsidies(case)
            checks = [
                {
                    "check_code": c.check_code,
                    "result": c.result,
                    "severity": c.severity,
                    "evidence": c.evidence,
                    "human_decision": c.human_decision,
                }
                for c in db.scalars(select(FraudCheck).where(FraudCheck.case_id == case_id))
            ]
            flags = [c for c in checks if c["result"] == "flag"]
            summary = case_summary(db, case)
            llm = get_llm_client()
            messages = [
                {"role": "system", "content": system_prompt()},
                {
                    "role": "user",
                    "content": user_prompt(
                        case_summary=summary,
                        subsidies=subsidies,
                        fraud_flags=flags,
                        pages=pages,
                        index=index,
                        pb=playbook_for_typology(case.typology),
                    )
                    + (
                        f"\n\n## Observações do operador\n{payload['context']}"
                        if payload.get("context")
                        else ""
                    ),
                },
            ]
            extracted: DossierExtraction | None = None
            call_id = None
            try:
                extracted, resp = llm.structured(
                    messages,
                    DossierExtraction,
                    purpose="dossier",
                    db=db,
                    tenant_id=tenant_id,
                    case_id=case_id,
                    prompt_version=DOSSIER_PROMPT_VERSION,
                    temperature=0,
                )
                call_id = resp.llm_call_id
            except ValueError as exc:
                log.warning("dossiê: saída estruturada inválida (%s)", exc)
                db.commit()  # preserva o llm_call com status
            pb = playbook_for_typology(case.typology)
            case_fields = {
                "comarca": case.comarca,
                "valor_causa": case.claim_value,
                "data_ajuizamento": case.filed_at.isoformat() if case.filed_at else None,
            }
            fields, sources = merge_fields(
                extracted=extracted.fields if extracted else {},
                subsidies=subsidies,
                fraud_checks=checks,
                case_fields=case_fields,
            )
            evaluation = evaluate_playbook(pb, fields)
            content: dict[str, Any] = {
                "generated_at": datetime.now(UTC).isoformat(),
                "prompt_version": DOSSIER_PROMPT_VERSION,
                "playbook": ({"id": pb.metadata.id, "versao": pb.metadata.versao} if pb else None),
                "page_index": index,
                "fields": fields,
                "field_sources": sources,
                "field_page_refs": {
                    k: resolve_refs(v, index)
                    for k, v in (extracted.field_page_refs if extracted else {}).items()
                },
                "facts": [
                    {"text": f.text, "document_page_ids": resolve_refs(f.page_refs, index)}
                    for f in (extracted.facts if extracted else [])
                ],
                "timeline": [
                    {
                        "date": e.date,
                        "event": e.event,
                        "document_page_ids": resolve_refs(e.page_refs, index),
                    }
                    for e in (extracted.timeline if extracted else [])
                ],
                "evidences": [
                    {
                        "description": e.description,
                        "document_page_ids": resolve_refs(e.page_refs, index),
                        "score": e.score,
                        "favors": e.favors,
                    }
                    for e in (extracted.evidences if extracted else [])
                ],
                "claims": extracted.claims if extracted else [],
                "weaknesses": extracted.weaknesses if extracted else [],
                "open_questions": extracted.open_questions if extracted else [],
                "exposure_basis": extracted.exposure_basis if extracted else None,
                "fraud_flags": [
                    {"check_code": c["check_code"], "severity": c["severity"]} for c in flags
                ],
                "fraud_note": "flags são indícios; nenhum rótulo sem decisão humana (M4)",
                **evaluation,
                "extraction_ok": extracted is not None,
            }
            last = db.scalar(
                select(Dossier.version)
                .where(Dossier.case_id == case_id)
                .order_by(Dossier.version.desc())
                .limit(1)
            )
            exposure = extracted.exposure_estimate if extracted else None
            if exposure is None and case.claim_value:
                exposure = case.claim_value
            dossier = Dossier(
                tenant_id=tenant_id,
                case_id=case_id,
                version=(last or 0) + 1,
                content=content,
                exposure_estimate=exposure,
                llm_call_id=call_id,
                status="ready" if extracted is not None else "failed",
            )
            db.add(dossier)
            db.flush()
            record(
                db,
                tenant_id=tenant_id,
                actor_user_id=None,
                actor_oab=None,
                action="dossier.build",
                entity_type="dossier",
                entity_id=dossier.id,
                payload={
                    "case_id": str(case_id),
                    "applicable_theses": [t["code"] for t in evaluation["applicable_theses"]],
                    "exceptions": [x["id"] for x in evaluation["exceptions_triggered"]],
                    "llm_call_id": str(call_id) if call_id else None,
                },
            )
            db.commit()
            return {
                "dossier_id": str(dossier.id),
                "status": dossier.status,
                "applicable_theses": [t["code"] for t in evaluation["applicable_theses"]],
                "exceptions_triggered": [x["id"] for x in evaluation["exceptions_triggered"]],
            }
    finally:
        current_tenant_id.reset(token)
