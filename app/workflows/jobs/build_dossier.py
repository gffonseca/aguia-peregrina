"""M5: consolida páginas + subsídios + antifraude em um dossiê estruturado."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.db import SessionLocal
from app.core.tenancy import current_tenant_id
from app.llm import get_llm_client
from app.models.litigation import Dossier
from app.modules.m05_dossie.service import DOSSIER_PROMPT_VERSION, DossierContent, system_prompt


def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = uuid.UUID(payload["tenant_id"])
    case_id = uuid.UUID(payload["case_id"])
    token = current_tenant_id.set(tenant_id)
    try:
        with SessionLocal() as db:
            llm = get_llm_client()
            messages = [
                {"role": "system", "content": system_prompt()},
                {"role": "user", "content": payload.get("context", "")},
            ]
            try:
                content, resp = llm.structured(
                    messages,
                    DossierContent,
                    purpose="dossier",
                    db=db,
                    tenant_id=tenant_id,
                    case_id=case_id,
                    prompt_version=DOSSIER_PROMPT_VERSION,
                )
                data, call_id = content.model_dump(), resp.llm_call_id
            except ValueError:
                data, call_id = {}, None
            dossier = Dossier(
                tenant_id=tenant_id,
                case_id=case_id,
                content=data,
                exposure_estimate=data.get("exposure_estimate"),
                llm_call_id=call_id,
            )
            db.add(dossier)
            db.commit()
            return {"dossier_id": str(dossier.id)}
    finally:
        current_tenant_id.reset(token)
