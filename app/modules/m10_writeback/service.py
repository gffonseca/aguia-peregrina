from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.integrations.erp.base import ErpConnector
from app.models.litigation import ErpWriteback, Outcome


def enqueue_writeback(
    db: Session, *, tenant_id: uuid.UUID, outcome: Outcome, connector: ErpConnector
) -> ErpWriteback:
    wb = ErpWriteback(
        tenant_id=tenant_id,
        case_id=outcome.case_id,
        connector=connector.name,
        payload=connector.serialize_outcome(outcome),
    )
    db.add(wb)
    return wb
