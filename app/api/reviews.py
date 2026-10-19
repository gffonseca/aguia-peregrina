"""M7 — Revisão. A exportação é bloqueada até `approved_at` (princípio OAB)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, tenant_id_dep
from app.core.audit import record
from app.core.security import Principal, require_lawyer
from app.models.litigation import Draft, Review
from app.modules.m07_revisao.service import (
    ReviewError,
    approve,
    assert_exportable,
    open_review,
    reject,
)
from app.schemas.litigation import RejectIn, ReviewOut

router = APIRouter(prefix="/reviews", tags=["reviews (M7)"])


def _draft_or_404(db: Session, draft_id: uuid.UUID) -> Draft:
    draft = db.get(Draft, draft_id)
    if draft is None:
        raise HTTPException(404, "minuta não encontrada")
    return draft


def _latest_review(db: Session, draft_id: uuid.UUID) -> Review | None:
    return db.scalar(
        select(Review).where(Review.draft_id == draft_id).order_by(Review.opened_at.desc()).limit(1)
    )


@router.post("/drafts/{draft_id}/open", response_model=ReviewOut, status_code=201)
def open_(
    draft_id: uuid.UUID,
    db: Session = DB,
    principal: Principal = Depends(require_lawyer),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> Review:
    draft = _draft_or_404(db, draft_id)
    review = open_review(
        db,
        tenant_id=tenant_id,
        draft=draft,
        reviewer_user_id=principal.user_id,
        reviewer_oab=principal.oab or "",
    )
    db.commit()
    return review


@router.post("/{review_id}/approve", response_model=ReviewOut)
def approve_(
    review_id: uuid.UUID,
    db: Session = DB,
    principal: Principal = Depends(require_lawyer),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(404, "revisão não encontrada")
    if review.reviewer_user_id != principal.user_id:
        raise HTTPException(403, "só o revisor que abriu pode aprovar")
    draft = _draft_or_404(db, review.draft_id)
    try:
        approve(review, draft)
    except ReviewError as exc:
        raise HTTPException(409, str(exc)) from exc
    record(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal.user_id,
        actor_oab=principal.oab,
        action="draft.approve",
        entity_type="draft",
        entity_id=draft.id,
        payload={"review_id": str(review.id), "review_seconds": review.review_seconds},
    )
    db.commit()
    return review


@router.post("/{review_id}/reject", response_model=ReviewOut)
def reject_(
    review_id: uuid.UUID,
    body: RejectIn,
    db: Session = DB,
    principal: Principal = Depends(require_lawyer),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(404, "revisão não encontrada")
    draft = _draft_or_404(db, review.draft_id)
    try:
        reject(review, draft, reason=body.reason)
    except ReviewError as exc:
        raise HTTPException(422, str(exc)) from exc
    record(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal.user_id,
        actor_oab=principal.oab,
        action="draft.reject",
        entity_type="draft",
        entity_id=draft.id,
        payload={"reason": body.reason},
    )
    db.commit()
    return review


@router.get("/drafts/{draft_id}/export", response_class=PlainTextResponse)
def export_(
    draft_id: uuid.UUID,
    db: Session = DB,
    principal: Principal = Depends(require_lawyer),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> str:
    """Exporta a peça (Markdown no esqueleto; DOCX depois). Bloqueado sem aprovação."""
    draft = _draft_or_404(db, draft_id)
    review = _latest_review(db, draft_id)
    try:
        assert_exportable(draft, review)
    except ReviewError as exc:
        raise HTTPException(423, str(exc)) from exc
    assert review is not None
    record(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal.user_id,
        actor_oab=principal.oab,
        action="draft.export",
        entity_type="draft",
        entity_id=draft.id,
        payload={"approved_by_oab": review.reviewer_oab},
    )
    db.commit()
    header = f"<!-- aprovado por OAB {review.reviewer_oab} em {review.approved_at} -->\n"
    return header + draft.body_markdown
