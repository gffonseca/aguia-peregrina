from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import DB, principal_in_tenant, tenant_id_dep
from app.core import cnj
from app.core.audit import record
from app.core.security import Principal
from app.models.litigation import Case, CaseParty
from app.schemas.litigation import CaseIn, CaseOut

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=list[CaseOut])
def list_cases(
    db: Session = DB,
    _: Principal = Depends(principal_in_tenant),
    cnj_number: str | None = None,
    external_ref: str | None = None,
) -> list[Case]:
    stmt = select(Case).options(selectinload(Case.parties))
    if cnj_number:
        stmt = stmt.where(Case.cnj_number == (cnj.normalize(cnj_number) or cnj_number))
    if external_ref:
        stmt = stmt.where(Case.external_ref == external_ref)
    return list(db.scalars(stmt.order_by(Case.created_at.desc()).limit(200)))


@router.post("", response_model=CaseOut, status_code=201)
def create_case(
    body: CaseIn,
    db: Session = DB,
    principal: Principal = Depends(principal_in_tenant),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> Case:
    """M1 — intake manual. Normaliza o CNJ (valida dígito verificador) e deriva o tribunal."""
    parsed = cnj.parse(body.cnj_number)
    if parsed is None or not parsed.is_valid:
        raise HTTPException(422, "número CNJ inválido (formato ou dígito verificador)")
    data = body.model_dump(exclude={"parties"})
    data["cnj_number"] = parsed.formatted
    data["court"] = data.get("court") or parsed.court
    existing = db.scalar(select(Case).where(Case.cnj_number == parsed.formatted))
    if existing is not None:
        raise HTTPException(409, f"processo já cadastrado: {existing.id}")
    case = Case(tenant_id=tenant_id, **data)
    case.meta = {"cnj": parsed.as_dict()}
    db.add(case)
    db.flush()
    for p in body.parties:
        db.add(CaseParty(tenant_id=tenant_id, case_id=case.id, **p.model_dump()))
    record(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal.user_id,
        actor_oab=principal.oab,
        action="case.create",
        entity_type="case",
        entity_id=case.id,
        payload={"cnj_number": case.cnj_number, "typology": case.typology},
    )
    db.commit()
    return _get(db, case.id)


def _get(db: Session, case_id: uuid.UUID) -> Case:
    case = db.scalar(select(Case).options(selectinload(Case.parties)).where(Case.id == case_id))
    if case is None:
        raise HTTPException(404, "processo não encontrado")
    return case


@router.get("/{case_id}", response_model=CaseOut)
def get_case(
    case_id: uuid.UUID, db: Session = DB, _: Principal = Depends(principal_in_tenant)
) -> Case:
    return _get(db, case_id)
