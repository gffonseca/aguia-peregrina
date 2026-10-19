"""M9: classifica e resume publicação com modelo pequeno; define alerta e prazo."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.db import SessionLocal
from app.core.tenancy import current_tenant_id
from app.llm import get_llm_client
from app.models.litigation import Publication
from app.modules.m09_monitoramento.service import PublicationSummary, alert_level_for


def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = uuid.UUID(payload["tenant_id"])
    token = current_tenant_id.set(tenant_id)
    try:
        with SessionLocal() as db:
            pub = db.get(Publication, uuid.UUID(payload["publication_id"]))
            if pub is None:
                return {"error": "publication not found"}
            llm = get_llm_client()
            try:
                summary, _ = llm.structured(
                    [{"role": "user", "content": pub.raw_text or ""}],
                    PublicationSummary,
                    purpose="publication_summary",
                    db=db,
                    tenant_id=tenant_id,
                    case_id=pub.case_id,
                    model=llm.settings.llm_small_model,
                )
                pub.category = summary.category
                pub.summary = summary.summary
                if summary.deadline_days is not None:
                    pub.deadline_at = (
                        datetime.now(UTC) + timedelta(days=summary.deadline_days)
                    ).date()
                pub.alert_level = alert_level_for(summary.category, summary.deadline_days)
            except ValueError:
                pub.category, pub.alert_level = "outro", "info"
            pub.processed_at = datetime.now(UTC)
            db.commit()
            return {"publication_id": str(pub.id), "alert_level": pub.alert_level}
    finally:
        current_tenant_id.reset(token)
