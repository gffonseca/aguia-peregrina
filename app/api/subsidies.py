"""M3 — subsídios do cliente (vínculo processo ↔ registro interno) e checklist de faltantes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import DB, principal_in_tenant, tenant_id_dep
from app.core.audit import record
from app.core.security import Principal
from app.models.litigation import Case
from app.modules.m00_playbook.service import playbook_for_typology
from app.modules.m03_subsidios.service import checklist_for_case, get_subsidies, set_subsidies

router = APIRouter(prefix="/cases/{case_id}/subsidies", tags=["subsidies (M3)"])


class SubsidiesIn(BaseModel):
    fields: dict[str, Any] = Field(
        description="campos de origem `subsidio` do playbook (ex.: contrato_localizado)"
    )
    replace: bool = False
    source_ref: str | None = Field(default=None, description="id do registro no ERP do cliente")


class ChecklistOut(BaseModel):
    typology: str
    present: list[str]
    missing: list[str]
    complete: bool
    subsidy_fields_missing: list[str]
    blocking_fields_missing: list[str]


def _case_or_404(db: Session, case_id: uuid.UUID) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(404, "processo não encontrado")
    return case


@router.get("", response_model=dict)
def get_(case_id: uuid.UUID, db: Session = DB, _: Principal = Depends(principal_in_tenant)) -> dict:
    return get_subsidies(_case_or_404(db, case_id))


@router.put("", response_model=dict)
def put_(
    case_id: uuid.UUID,
    body: SubsidiesIn,
    db: Session = DB,
    principal: Principal = Depends(principal_in_tenant),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> dict:
    case = _case_or_404(db, case_id)
    data = dict(body.fields)
    if body.source_ref:
        data["_source_ref"] = body.source_ref
    merged = set_subsidies(db, case=case, data=data, replace=body.replace)
    record(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal.user_id,
        actor_oab=principal.oab,
        action="subsidies.set",
        entity_type="case",
        entity_id=case.id,
        payload={"fields": sorted(body.fields), "source_ref": body.source_ref},
    )
    db.commit()
    return merged


@router.get("/checklist", response_model=ChecklistOut)
def checklist(
    case_id: uuid.UUID, db: Session = DB, _: Principal = Depends(principal_in_tenant)
) -> ChecklistOut:
    """Checklist determinístico: provas da tipologia × páginas/subsídios presentes; campos de
    subsídio do playbook ainda não informados (e quais bloqueiam a minuta)."""
    case = _case_or_404(db, case_id)
    pb = playbook_for_typology(case.typology)
    subsidy_missing: list[str] = []
    blocking_missing: list[str] = []
    if pb is not None:
        subs = get_subsidies(case)
        for c in pb.campos_dossie_obrigatorios:
            if c.origem.value == "subsidio" and c.obrigatorio and subs.get(c.campo) is None:
                subsidy_missing.append(c.campo)
                if c.bloqueia_minuta_se_ausente:
                    blocking_missing.append(c.campo)
    ck = checklist_for_case(db, case=case)
    return ChecklistOut(
        typology=ck.typology,
        present=sorted(ck.present),
        missing=ck.missing,
        complete=ck.complete,
        subsidy_fields_missing=subsidy_missing,
        blocking_fields_missing=blocking_missing,
    )
