from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, principal_in_tenant, tenant_id_dep
from app.api.jobs import dispatch
from app.core.security import Principal
from app.models.litigation import Case, Dossier
from app.schemas.litigation import DossierOut

router = APIRouter(prefix="/dossiers", tags=["dossiers (M5)"])


@router.post("/cases/{case_id}/build", status_code=202)
def build(
    case_id: uuid.UUID,
    db: Session = DB,
    _: Principal = Depends(principal_in_tenant),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
    wait: bool = False,
) -> dict:
    """`wait=false` (default): roda em background e devolve `job` para `GET /jobs/{ref}`."""
    if db.get(Case, case_id) is None:
        raise HTTPException(404, "processo não encontrado")
    return dispatch(
        "build_dossier",
        {"tenant_id": str(tenant_id), "case_id": str(case_id), "context": ""},
        wait=wait,
    )


@router.get("/cases/{case_id}", response_model=list[DossierOut])
def list_dossiers(
    case_id: uuid.UUID, db: Session = DB, _: Principal = Depends(principal_in_tenant)
) -> list[Dossier]:
    return list(db.scalars(select(Dossier).where(Dossier.case_id == case_id)))
