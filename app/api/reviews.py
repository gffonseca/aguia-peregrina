"""M7 — Revisão. A exportação é bloqueada até `approved_at` (princípio OAB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, tenant_id_dep
from app.core.audit import record
from app.core.security import Principal, require_lawyer
from app.models.litigation import Case, Draft, Review, ThesisVersion
from app.models.tenant import Tenant
from app.modules.m07_revisao.docx_export import CoverInfo, render_docx
from app.modules.m07_revisao.service import (
    ReviewError,
    approve,
    assert_exportable,
    open_review,
    reject,
    review_min_seconds_for,
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


def _tenant_settings(db: Session, tenant_id: uuid.UUID) -> dict:
    tenant = db.get(Tenant, tenant_id)
    return dict(tenant.settings or {}) if tenant else {}


@router.get("/drafts/{draft_id}", response_model=list[ReviewOut])
def list_(
    draft_id: uuid.UUID, db: Session = DB, _: Principal = Depends(require_lawyer)
) -> list[Review]:
    return list(
        db.scalars(select(Review).where(Review.draft_id == draft_id).order_by(Review.opened_at))
    )


@router.post("/drafts/{draft_id}/open", response_model=ReviewOut, status_code=201)
def open_(
    draft_id: uuid.UUID,
    db: Session = DB,
    principal: Principal = Depends(require_lawyer),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> Review:
    draft = _draft_or_404(db, draft_id)
    if draft.status in {"approved", "exported"}:
        raise HTTPException(409, "minuta já aprovada")
    current = _latest_review(db, draft_id)
    if (
        current is not None
        and current.decision is None
        and current.reviewer_user_id == principal.user_id
    ):
        return current  # idempotente: a revisão aberta pelo mesmo advogado continua
    review = open_review(
        db,
        tenant_id=tenant_id,
        draft=draft,
        reviewer_user_id=principal.user_id,
        reviewer_oab=principal.oab or "",
    )
    db.flush()
    record(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal.user_id,
        actor_oab=principal.oab,
        action="review.open",
        entity_type="draft",
        entity_id=draft.id,
        payload={
            "review_id": str(review.id),
            "min_seconds": review_min_seconds_for(
                draft.draft_type, _tenant_settings(db, tenant_id)
            ),
        },
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
    minimum = review_min_seconds_for(draft.draft_type, _tenant_settings(db, tenant_id))
    try:
        approve(review, draft, minimum=minimum)
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
        payload={
            "review_id": str(review.id),
            "review_seconds": review.review_seconds,
            "min_seconds": minimum,
        },
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


def _cover(db: Session, draft: Draft, review: Review) -> CoverInfo:
    case = db.get(Case, draft.case_id)
    pb_id, pb_ver, pb_oab = None, None, None
    for vid in draft.thesis_version_ids or []:
        v = db.get(ThesisVersion, uuid.UUID(str(vid)))
        if v is not None:
            c = v.conditions or {}
            pb_id, pb_ver, pb_oab = (
                c.get("playbook_id"),
                c.get("playbook_versao"),
                v.approved_by_oab,
            )
            break
    approved_at = review.approved_at or datetime.now(UTC)
    return CoverInfo(
        generated_at=draft.created_at
        if draft.created_at.tzinfo
        else draft.created_at.replace(tzinfo=UTC),
        playbook_id=pb_id,
        playbook_version=pb_ver,
        playbook_approved_by_oab=pb_oab,
        reviewer_oab=review.reviewer_oab,
        approved_at=approved_at if approved_at.tzinfo else approved_at.replace(tzinfo=UTC),
        review_seconds=review.review_seconds,
        cnj_number=case.cnj_number if case else "—",
        draft_type=draft.draft_type,
        draft_version=draft.version,
    )


@router.get("/drafts/{draft_id}/export")
def export_(
    draft_id: uuid.UUID,
    format: Literal["md", "docx"] = "md",
    db: Session = DB,
    principal: Principal = Depends(require_lawyer),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> Response:
    """Exporta a peça (Markdown ou DOCX). Bloqueado (423) sem aprovação registrada."""
    draft = _draft_or_404(db, draft_id)
    review = _latest_review(db, draft_id)
    try:
        assert_exportable(draft, review)
    except ReviewError as exc:
        raise HTTPException(423, str(exc)) from exc
    assert review is not None
    cover = _cover(db, draft, review)
    record(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal.user_id,
        actor_oab=principal.oab,
        action="draft.export",
        entity_type="draft",
        entity_id=draft.id,
        payload={"approved_by_oab": review.reviewer_oab, "format": format},
    )
    draft.status = "exported"
    db.commit()
    if format == "docx":
        data = render_docx(draft.body_markdown, cover)
        name = f"minuta-{cover.cnj_number}-{draft.draft_type}-v{draft.version}.docx"
        return Response(
            content=data,
            media_type=("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )
    header = (
        f"<!-- {cover.cover_line()} | aprovado por OAB {review.reviewer_oab} "
        f"em {review.approved_at} -->\n"
    )
    return PlainTextResponse(header + draft.body_markdown)
