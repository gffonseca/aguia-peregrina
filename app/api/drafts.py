from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, principal_in_tenant, tenant_id_dep
from app.api.jobs import dispatch
from app.core.security import Principal
from app.models.litigation import Case, Draft
from app.schemas.litigation import DraftGenerateIn, DraftOut

router = APIRouter(prefix="/drafts", tags=["drafts (M6)"])


@router.post("/cases/{case_id}/generate", status_code=202)
def generate(
    case_id: uuid.UUID,
    body: DraftGenerateIn,
    db: Session = DB,
    _: Principal = Depends(principal_in_tenant),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
    wait: bool = False,
) -> dict:
    """`wait=false` (default): roda em background e devolve `job` para `GET /jobs/{ref}`."""
    if db.get(Case, case_id) is None:
        raise HTTPException(404, "processo não encontrado")
    return dispatch(
        "generate_draft",
        {
            "tenant_id": str(tenant_id),
            "case_id": str(case_id),
            "draft_type": body.draft_type,
            "dossier_id": str(body.dossier_id) if body.dossier_id else None,
            "context": body.context,
        },
        wait=wait,
    )


@router.get("/cases/{case_id}", response_model=list[DraftOut])
def list_drafts(
    case_id: uuid.UUID, db: Session = DB, _: Principal = Depends(principal_in_tenant)
) -> list[Draft]:
    return list(db.scalars(select(Draft).where(Draft.case_id == case_id)))


@router.get("/{draft_id}", response_model=DraftOut)
def get_draft(
    draft_id: uuid.UUID, db: Session = DB, _: Principal = Depends(principal_in_tenant)
) -> Draft:
    draft = db.get(Draft, draft_id)
    if draft is None:
        raise HTTPException(404, "minuta não encontrada")
    return draft
