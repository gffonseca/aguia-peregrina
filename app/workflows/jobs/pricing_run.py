"""N2: roda o pricing engine e persiste `pricing_runs` com hash da metodologia."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.db import SessionLocal
from app.core.tenancy import current_tenant_id
from app.models.credit import PricingRun
from app.modules.credit.pricing_engine import PricingInputs, Scenario, price


def inputs_from_payload(payload: dict[str, Any]) -> PricingInputs:
    scenarios = [Scenario(**s) for s in payload["scenarios"]]
    return PricingInputs(
        scenarios=scenarios,
        target_irr=payload.get("target_irr", 0.35),
        tax_rate=payload.get("tax_rate", 0.34),
        c_fix=payload.get("c_fix", 0.0),
        c_serv_pv=payload.get("c_serv_pv", 0.0),
        face_value=payload.get("face_value"),
        reference_value=payload.get("reference_value"),
        label=payload.get("label", ""),
    )


def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = uuid.UUID(payload["tenant_id"])
    token = current_tenant_id.set(tenant_id)
    try:
        inputs = inputs_from_payload(payload)
        result = price(inputs)
        with SessionLocal() as db:
            row = PricingRun(
                tenant_id=tenant_id,
                credit_asset_id=uuid.UUID(payload["credit_asset_id"])
                if payload.get("credit_asset_id")
                else None,
                methodology_version=result.methodology_version,
                params_hash=result.params_hash,
                inputs={k: v for k, v in payload.items() if k != "tenant_id"},
                outputs=result.as_dict(),
                p_max=result.p_max,
                offer_price=result.offer_high,
                expected_moic=result.expected_moic,
                expected_duration_years=result.expected_duration_years,
                run_by_user_id=uuid.UUID(payload["user_id"]) if payload.get("user_id") else None,
            )
            db.add(row)
            db.commit()
            return {"pricing_run_id": str(row.id), "p_max": result.p_max, "viable": result.viable}
    finally:
        current_tenant_id.reset(token)
