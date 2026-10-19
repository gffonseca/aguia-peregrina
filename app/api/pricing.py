"""N2 — Pricing. `POST /pricing/run` executa a fórmula e persiste `pricing_runs`."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DB, principal_in_tenant, tenant_id_dep
from app.core.security import Principal
from app.models.credit import PricingRun
from app.modules.credit.examples import ALL_EXAMPLES
from app.modules.credit.pricing_engine import PricingInputs, Scenario, price
from app.schemas.pricing import PricingRunIn, PricingRunOut

router = APIRouter(prefix="/pricing", tags=["pricing (N2)"])


def _to_out(result, run_id: uuid.UUID | None) -> PricingRunOut:  # type: ignore[no-untyped-def]
    d = result.as_dict()
    return PricingRunOut(
        pricing_run_id=str(run_id) if run_id else None,
        **{k: d[k] for k in PricingRunOut.model_fields if k != "pricing_run_id"},
    )


@router.post("/run", response_model=PricingRunOut)
def run(
    body: PricingRunIn,
    db: Session = DB,
    principal: Principal = Depends(principal_in_tenant),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> PricingRunOut:
    inputs = PricingInputs(
        scenarios=[Scenario(**s.model_dump()) for s in body.scenarios],
        target_irr=body.target_irr,
        tax_rate=body.tax_rate,
        c_fix=body.c_fix,
        c_serv_pv=body.c_serv_pv,
        face_value=body.face_value,
        reference_value=body.reference_value,
        label=body.label,
    )
    try:
        result = price(inputs)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    row = PricingRun(
        tenant_id=tenant_id,
        credit_asset_id=body.credit_asset_id,
        methodology_version=result.methodology_version,
        params_hash=result.params_hash,
        inputs=body.model_dump(mode="json"),
        outputs=result.as_dict(),
        p_max=result.p_max,
        offer_price=result.offer_high,
        expected_moic=result.expected_moic,
        expected_duration_years=result.expected_duration_years,
        run_by_user_id=principal.user_id,
    )
    db.add(row)
    db.commit()
    return _to_out(result, row.id)


@router.get("/examples/{name}", response_model=PricingRunOut)
def example(name: str, _: Principal = Depends(principal_in_tenant)) -> PricingRunOut:
    """Os quatro exemplos da nota técnica, sem persistir."""
    if name not in ALL_EXAMPLES:
        raise HTTPException(404, f"exemplos: {sorted(ALL_EXAMPLES)}")
    return _to_out(price(ALL_EXAMPLES[name]()), None)
