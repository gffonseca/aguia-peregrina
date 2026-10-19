from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, principal_in_tenant, tenant_id_dep
from app.core.audit import record
from app.core.security import Principal, require_lawyer
from app.models.litigation import Case, FraudCheck
from app.modules.m04_antifraude.service import human_decide, run_checks
from app.schemas.litigation import FraudCheckOut, FraudDecisionIn

router = APIRouter(prefix="/fraud", tags=["fraud (M4)"])


@router.post("/cases/{case_id}/run", response_model=list[FraudCheckOut])
def run(
    case_id: uuid.UUID,
    ctx: dict,
    db: Session = DB,
    _: Principal = Depends(principal_in_tenant),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> list[FraudCheck]:
    if db.get(Case, case_id) is None:
        raise HTTPException(404, "processo não encontrado")
    rows = run_checks(db, tenant_id=tenant_id, case_id=case_id, ctx=ctx)
    db.commit()
    return rows


@router.get("/cases/{case_id}", response_model=list[FraudCheckOut])
def list_checks(
    case_id: uuid.UUID, db: Session = DB, _: Principal = Depends(principal_in_tenant)
) -> list[FraudCheck]:
    return list(db.scalars(select(FraudCheck).where(FraudCheck.case_id == case_id)))


@router.post("/checks/{check_id}/decide", response_model=FraudCheckOut)
def decide(
    check_id: uuid.UUID,
    body: FraudDecisionIn,
    db: Session = DB,
    principal: Principal = Depends(require_lawyer),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> FraudCheck:
    """Único caminho para transformar um flag em decisão. Exige advogado + MFA + auditoria."""
    check = db.get(FraudCheck, check_id)
    if check is None:
        raise HTTPException(404, "checagem não encontrada")
    human_decide(check, decision=body.decision, oab=principal.oab or "")
    record(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal.user_id,
        actor_oab=principal.oab,
        action=f"fraud_check.{body.decision}",
        entity_type="fraud_check",
        entity_id=check.id,
        payload={"check_code": check.check_code},
    )
    db.commit()
    return check
