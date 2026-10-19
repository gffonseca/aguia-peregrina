from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ScenarioIn(BaseModel):
    name: str
    probability: float = Field(ge=0, le=1)
    cash_flow: float = Field(ge=0)
    t_years: float = Field(ge=0)


class PricingRunIn(BaseModel):
    credit_asset_id: uuid.UUID | None = None
    scenarios: list[ScenarioIn] = Field(min_length=1)
    target_irr: float = 0.35
    tax_rate: float = Field(default=0.34, ge=0, lt=1)
    c_fix: float = 0.0
    c_serv_pv: float = 0.0
    face_value: float | None = None
    reference_value: float | None = None
    label: str = ""


class PricingRunOut(BaseModel):
    pricing_run_id: str | None
    methodology_version: str
    pv_expected: float
    df_bar: float
    pre_tax_price: float
    p_max: float
    offer_low: float
    offer_high: float
    expected_moic: float | None
    expected_duration_years: float
    p_total_loss: float
    price_over_face: float | None
    price_over_reference: float | None
    viable: bool
    params_hash: str
