"""M6: gera minuta (sugestão) a partir de teses aprovadas + dossiê, com citações por página."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.db import SessionLocal
from app.core.tenancy import current_tenant_id
from app.llm import get_llm_client
from app.models.litigation import Draft, DraftCitation
from app.modules.m06_minuta.service import DRAFT_PROMPT_VERSION, DraftOutput, system_prompt


def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = uuid.UUID(payload["tenant_id"])
    case_id = uuid.UUID(payload["case_id"])
    draft_type = payload.get("draft_type", "contestacao")
    token = current_tenant_id.set(tenant_id)
    try:
        with SessionLocal() as db:
            llm = get_llm_client()
            messages = [
                {"role": "system", "content": system_prompt(draft_type)},
                {"role": "user", "content": payload.get("context", "")},
            ]
            body, citations, confidence, call_id = "", [], None, None
            try:
                out, resp = llm.structured(
                    messages,
                    DraftOutput,
                    purpose="draft",
                    db=db,
                    tenant_id=tenant_id,
                    case_id=case_id,
                    prompt_version=DRAFT_PROMPT_VERSION,
                )
                body, citations, confidence, call_id = (
                    out.body_markdown,
                    out.citations,
                    out.confidence,
                    resp.llm_call_id,
                )
            except ValueError:
                pass
            draft = Draft(
                tenant_id=tenant_id,
                case_id=case_id,
                dossier_id=uuid.UUID(payload["dossier_id"]) if payload.get("dossier_id") else None,
                draft_type=draft_type,
                body_markdown=body,
                confidence=confidence,
                llm_call_id=call_id,
            )
            db.add(draft)
            db.flush()
            for c in citations:
                db.add(
                    DraftCitation(
                        tenant_id=tenant_id,
                        draft_id=draft.id,
                        document_page_id=uuid.UUID(c.document_page_id),
                        quote=c.quote,
                        anchor=c.anchor,
                        evidence_score=c.evidence_score,
                    )
                )
            db.commit()
            return {"draft_id": str(draft.id), "status": draft.status}
    finally:
        current_tenant_id.reset(token)
