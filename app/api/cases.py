from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, principal_in_tenant, tenant_id_dep
from app.core.audit import record
from app.core.security import Principal
from app.models.litigation import Case
from app.schemas.litigation import CaseIn, CaseOut

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=list[CaseOut])
def list_cases(db: Session = DB, _: Principal = Depends(principal_in_tenant)) -> list[Case]:
    return list(db.scalars(select(Case).order_by(Case.created_at.desc()).limit(200)))


@router.post("", response_model=CaseOut, status_code=201)
def create_case(
    body: CaseIn,
    db: Session = DB,
    principal: Principal = Depends(principal_in_tenant),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> Case:
    case = Case(tenant_id=tenant_id, **body.model_dump())
    db.add(case)
    db.flush()
    record(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal.user_id,
        actor_oab=principal.oab,
        action="case.create",
        entity_type="case",
        entity_id=case.id,
        payload={"cnj_number": case.cnj_number},
    )
    db.commit()
    return case


@router.get("/{case_id}", response_model=CaseOut)
def get_case(
    case_id: uuid.UUID, db: Session = DB, _: Principal = Depends(principal_in_tenant)
) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(404, "processo não encontrado")
    return case
