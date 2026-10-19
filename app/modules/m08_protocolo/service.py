from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.litigation import Draft, Filing, Review
from app.modules.m07_revisao.service import assert_exportable


def register_filing(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    draft: Draft,
    review: Review,
    filed_by_user_id: uuid.UUID,
    filed_by_oab: str,
    receipt_storage_key: str | None,
) -> Filing:
    assert_exportable(draft, review)
    filing = Filing(
        tenant_id=tenant_id,
        case_id=draft.case_id,
        draft_id=draft.id,
        review_id=review.id,
        filed_by_user_id=filed_by_user_id,
        filed_by_oab=filed_by_oab,
        filed_at=datetime.now(UTC),
        receipt_storage_key=receipt_storage_key,
    )
    draft.status = "exported"
    db.add(filing)
    return filing
