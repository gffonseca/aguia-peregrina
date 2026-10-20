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


def review_min_seconds_for(draft_type: str, tenant_settings: dict | None = None) -> int:
    """Tempo mínimo de revisão: configuração global por tipo de peça.

    Só um tenant marcado como `test_mode: true` em `tenants.settings` pode reduzir o mínimo
    (`review_min_seconds: {"contestacao": 30, "default": 30}`), e nunca abaixo de 5 s — serve
    ao piloto sintético, nunca a dados reais. Fora do modo de teste a chave é ignorada.
    """
    base = get_settings().review_min_seconds(draft_type)
    ts = tenant_settings or {}
    if not ts.get("test_mode"):
        return base
    override = ts.get("review_min_seconds") or {}
    if isinstance(override, int | float):
        return max(5, int(override))
    value = override.get(draft_type, override.get("default"))
    return max(5, int(value)) if value is not None else base


def approve(
    review: Review,
    draft: Draft,
    *,
    now: datetime | None = None,
    minimum: int | None = None,
) -> Review:
    """Aprovação exige tempo mínimo de revisão por tipo de peça (direito de leitura real)."""
    now = now or datetime.now(UTC)
    opened = review.opened_at
    if opened.tzinfo is None:  # SQLite devolve naive
        opened = opened.replace(tzinfo=UTC)
    elapsed = int((now - opened).total_seconds())
    if minimum is None:
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
    opened = review.opened_at if review.opened_at.tzinfo else review.opened_at.replace(tzinfo=UTC)
    review.rejected_at = now
    review.decision = "rejected"
    review.rejection_reason = reason
    review.review_seconds = int((now - opened).total_seconds())
    draft.status = "rejected"
    return review


def assert_exportable(draft: Draft, review: Review | None) -> None:
    """Bloqueio de exportação sem aprovação. Chamado por qualquer rota de export/DOCX."""
    if review is None or review.approved_at is None or draft.status not in {"approved", "exported"}:
        raise ReviewError("exportação bloqueada: peça sem aprovação registrada por advogado")
