from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.litigation import Thesis, ThesisVersion


def create_version(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    thesis: Thesis,
    body_markdown: str,
    conditions: dict,
    author_user_id: uuid.UUID,
    author_oab: str,
) -> ThesisVersion:
    last = db.scalar(
        select(ThesisVersion.version)
        .where(ThesisVersion.thesis_id == thesis.id)
        .order_by(ThesisVersion.version.desc())
        .limit(1)
    )
    version = ThesisVersion(
        tenant_id=tenant_id,
        thesis_id=thesis.id,
        version=(last or 0) + 1,
        body_markdown=body_markdown,
        conditions=conditions,
        author_user_id=author_user_id,
        author_oab=author_oab,
    )
    db.add(version)
    return version


def approve_version(
    version: ThesisVersion, *, approver_user_id: uuid.UUID, approver_oab: str
) -> None:
    """Só sócio/advogado com OAB aprova; a aprovação torna a versão a corrente."""
    version.approved_by_user_id = approver_user_id
    version.approved_by_oab = approver_oab
    version.approved_at = datetime.now(UTC)
