from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.publications.base import PublicationRecord
from app.models.litigation import Case, Publication


def ingest(db: Session, *, tenant_id: uuid.UUID, record: PublicationRecord) -> Publication:
    """Idempotente por (provider, provider_ref). Vincula ao caso pelo número CNJ se existir."""
    existing = db.scalar(
        select(Publication).where(
            Publication.provider == record.provider,
            Publication.provider_ref == record.provider_ref,
        )
    )
    if existing:
        return existing
    case_id = db.scalar(select(Case.id).where(Case.cnj_number == record.cnj_number))
    pub = Publication(
        tenant_id=tenant_id,
        case_id=case_id,
        provider=record.provider,
        provider_ref=record.provider_ref,
        cnj_number=record.cnj_number,
        published_at=record.published_at,
        raw_text=record.text,
    )
    db.add(pub)
    return pub
