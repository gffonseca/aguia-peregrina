"""Sync incremental do Legal One (processos, partes, contatos, andamentos, tarefas).

Payload: `{"tenant_id": uuid, "since": "YYYY-MM-DD" | "auto" | null,
           "max_pages": int | null, "resources": ["lawsuits", ...] | null}`.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Any

from app.core.db import SessionLocal
from app.core.tenancy import current_tenant_id
from app.integrations.legalone.client import LegalOneClient, get_legalone_client
from app.integrations.legalone.sync import DEFAULT_RESOURCES, LegalOneSync

log = logging.getLogger(__name__)


def run(payload: dict[str, Any], *, client: LegalOneClient | None = None) -> dict[str, Any]:
    tenant_id = uuid.UUID(str(payload["tenant_id"]))
    max_pages = payload.get("max_pages")
    resources = tuple(payload.get("resources") or DEFAULT_RESOURCES)
    token = current_tenant_id.set(tenant_id)
    try:
        with SessionLocal() as db:
            sync = LegalOneSync(db, tenant_id=tenant_id, client=client or get_legalone_client())
            since_raw = payload.get("since")
            since: date | None
            if since_raw == "auto":
                since = sync.last_successful_since()
            elif since_raw:
                since = date.fromisoformat(str(since_raw))
            else:
                since = None
            log.info(
                "sync_legalone tenant=%s since=%s max_pages=%s resources=%s",
                tenant_id,
                since,
                max_pages,
                resources,
            )
            result = sync.run(
                since=since,
                max_pages=int(max_pages) if max_pages else None,
                resources=resources,
            )
            result["since"] = since.isoformat() if since else None
            return result
    finally:
        current_tenant_id.reset(token)
