from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.litigation import Draft, Review


class ReviewError(PermissionError):
    pass


def open_review(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    draft: Draft,
    reviewer_user_id: uuid.UUID,
    reviewer_oab: str,
) -> Review:
    if not reviewer_oab:
        raise ReviewError("revisor sem OAB")
    review = Review(
        tenant_id=tenant_id,
        draft_id=draft.id,
        reviewer_user_id=reviewer_user_id,
        reviewer_oab=reviewer_oab,
        opened_at=datetime.now(UTC),
    )
    draft.status = "in_review"
    db.add(review)
    return review


def approve(review: Review, draft: Draft, *, now: datetime | None = None) -> Review:
    """Aprovação exige tempo mínimo de revisão por tipo de peça (direito de leitura real)."""
    now = now or datetime.now(UTC)
    elapsed = int((now - review.opened_at).total_seconds())
    minimum = get_settings().review_min_seconds(draft.draft_type)
    if elapsed < minimum:
        raise ReviewError(f"tempo mínimo de revisão não atingido ({elapsed}s < {minimum}s)")
    review.approved_at = now
    review.decision = "approved"
    review.review_seconds = elapsed
    draft.status = "approved"
    return review


def reject(review: Review, draft: Draft, *, reason: str) -> Review:
    """Direito de recusa: sempre com motivo registrado."""
    if not reason or len(reason.strip()) < 10:
        raise ReviewError("recusa exige motivo (mínimo 10 caracteres)")
    now = datetime.now(UTC)
    review.rejected_at = now
    review.decision = "rejected"
    review.rejection_reason = reason
    review.review_seconds = int((now - review.opened_at).total_seconds())
    draft.status = "rejected"
    return review


def assert_exportable(draft: Draft, review: Review | None) -> None:
    """Bloqueio de exportação sem aprovação. Chamado por qualquer rota de export/DOCX."""
    if review is None or review.approved_at is None or draft.status not in {"approved", "exported"}:
        raise ReviewError("exportação bloqueada: peça sem aprovação registrada por advogado")
