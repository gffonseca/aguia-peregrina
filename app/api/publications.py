from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, principal_in_tenant, tenant_id_dep
from app.core.config import get_settings
from app.core.security import Principal
from app.integrations.publications import get_publications_provider
from app.models.litigation import Publication
from app.schemas.litigation import PublicationOut
from app.workflows.engine import get_engine

router = APIRouter(prefix="/publications", tags=["publications (M1/M9)"])


@router.get("", response_model=list[PublicationOut])
def list_publications(
    db: Session = DB, _: Principal = Depends(principal_in_tenant)
) -> list[Publication]:
    return list(
        db.scalars(select(Publication).order_by(Publication.published_at.desc()).limit(200))
    )


@router.post("/webhook/{provider}", status_code=202)
def webhook(
    provider: str,
    payload: dict,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> dict:
    """Recebe publicações do provedor e enfileira intake. Autenticar por segredo de webhook."""
    prov = get_publications_provider(provider or get_settings().publications_provider)
    records = prov.parse_webhook(payload)
    engine = get_engine()
    refs = [
        engine.dispatch("intake_publication", {"tenant_id": str(tenant_id), "record": r.__dict__})
        for r in records
    ]
    return {"queued": len(refs)}
