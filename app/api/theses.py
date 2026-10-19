from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, principal_in_tenant, tenant_id_dep
from app.core.security import Principal, require_lawyer
from app.models.litigation import Thesis, ThesisVersion
from app.modules.m00_playbook.service import approve_version, create_version
from app.schemas.litigation import ThesisIn, ThesisOut, ThesisVersionIn

router = APIRouter(prefix="/theses", tags=["theses (M0)"])


@router.get("", response_model=list[ThesisOut])
def list_theses(db: Session = DB, _: Principal = Depends(principal_in_tenant)) -> list[Thesis]:
    return list(db.scalars(select(Thesis).where(Thesis.is_active.is_(True))))


@router.post("", response_model=ThesisOut, status_code=201)
def create_thesis(
    body: ThesisIn,
    db: Session = DB,
    _: Principal = Depends(require_lawyer),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> Thesis:
    thesis = Thesis(tenant_id=tenant_id, **body.model_dump())
    db.add(thesis)
    db.commit()
    return thesis


@router.post("/{thesis_id}/versions", status_code=201)
def add_version(
    thesis_id: uuid.UUID,
    body: ThesisVersionIn,
    db: Session = DB,
    principal: Principal = Depends(require_lawyer),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> dict:
    thesis = db.get(Thesis, thesis_id)
    if thesis is None:
        raise HTTPException(404, "tese não encontrada")
    v = create_version(
        db,
        tenant_id=tenant_id,
        thesis=thesis,
        body_markdown=body.body_markdown,
        conditions=body.conditions,
        author_user_id=principal.user_id,
        author_oab=principal.oab or "",
    )
    db.commit()
    return {"version_id": str(v.id), "version": v.version}


@router.post("/{thesis_id}/versions/{version_id}/approve")
def approve(
    thesis_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = DB,
    principal: Principal = Depends(require_lawyer),
) -> dict:
    v = db.get(ThesisVersion, version_id)
    thesis = db.get(Thesis, thesis_id)
    if v is None or thesis is None or v.thesis_id != thesis_id:
        raise HTTPException(404, "versão não encontrada")
    approve_version(v, approver_user_id=principal.user_id, approver_oab=principal.oab or "")
    thesis.current_version_id = v.id
    db.commit()
    return {"approved_by_oab": v.approved_by_oab, "approved_at": v.approved_at}
