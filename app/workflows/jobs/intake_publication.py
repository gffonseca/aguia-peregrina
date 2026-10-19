"""M1: recebe payload de publicação (webhook/polling) e grava em `publications`."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.db import SessionLocal
from app.core.tenancy import current_tenant_id
from app.integrations.publications.base import PublicationRecord
from app.modules.m01_intake.service import ingest


def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = uuid.UUID(payload["tenant_id"])
    token = current_tenant_id.set(tenant_id)
    try:
        with SessionLocal() as db:
            record = PublicationRecord(**payload["record"])
            pub = ingest(db, tenant_id=tenant_id, record=record)
            db.commit()
            return {"publication_id": str(pub.id), "next": "monitor_publication"}
    finally:
        current_tenant_id.reset(token)
