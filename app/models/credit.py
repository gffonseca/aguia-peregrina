"""Lado compra de créditos (N1–N7)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JSONType, TenantModel


class Cedente(TenantModel):
    """N1 Originação/CRM: titular do crédito. Registro de base legal LGPD e opt-out."""

    __tablename__ = "cedentes"
    name: Mapped[str] = mapped_column(String(300))
    document: Mapped[str | None] = mapped_column(String(20), index=True)
    contact: Mapped[dict] = mapped_column(JSONType, default=dict)
    lead_source: Mapped[str | None] = mapped_column(String(60))  # datajud|djen|indicacao|inbound
    lgpd_basis: Mapped[str | None] = mapped_column(String(60))
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)
    excluded_reason: Mapped[str | None] = mapped_column(String(200))  # ex.: cliente FBS (muralha)
    funnel_stage: Mapped[str] = mapped_column(String(30), default="candidate")


class CreditAsset(TenantModel):
    """Crédito judicial candidato ou comprado."""

    __tablename__ = "credit_assets"
    cedente_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("cedentes.id"))
    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    asset_type: Mapped[str] = mapped_column(
        String(40)
    )  # civel_transitado|civel_conhecimento|trabalhista|pre_ajuizamento|precatorio
    typology: Mapped[str | None] = mapped_column(String(60))
    debtor_name: Mapped[str | None] = mapped_column(String(300))
    debtor_document: Mapped[str | None] = mapped_column(String(20), index=True)
    face_value: Mapped[float] = mapped_column(Float)
    face_value_date: Mapped[date | None] = mapped_column(Date)
    phase: Mapped[str | None] = mapped_column(String(40))
    court: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(30), default="candidate"
    )  # candidate|priced|offered|bought|collected|written_off
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("portfolios.id"))
    meta: Mapped[dict] = mapped_column(JSONType, default=dict)


class PricingRun(TenantModel):
    """N2: cotação. Guarda inputs, versão da metodologia e saídas."""

    __tablename__ = "pricing_runs"
    credit_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("credit_assets.id"), index=True
    )
    methodology_version: Mapped[str] = mapped_column(String(20))
    params_hash: Mapped[str] = mapped_column(String(64))
    inputs: Mapped[dict] = mapped_column(JSONType, default=dict)
    outputs: Mapped[dict] = mapped_column(JSONType, default=dict)
    p_max: Mapped[float | None] = mapped_column(Float)
    offer_price: Mapped[float | None] = mapped_column(Float)
    expected_moic: Mapped[float | None] = mapped_column(Float)
    expected_duration_years: Mapped[float | None] = mapped_column(Float)
    run_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class Contract(TenantModel):
    """N3: instrumento de cessão / promessa / funding."""

    __tablename__ = "contracts"
    credit_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("credit_assets.id"), index=True
    )
    pricing_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("pricing_runs.id"))
    contract_type: Mapped[str] = mapped_column(String(30))  # cessao|cessao_parcial|exito|funding
    price: Mapped[float] = mapped_column(Float)
    template_version: Mapped[str | None] = mapped_column(String(40))
    storage_key: Mapped[str | None] = mapped_column(String(500))
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signature_provider_ref: Mapped[str | None] = mapped_column(String(200))
    debtor_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # CC 290
    habilitation_filed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="draft")


class CollectionEvent(TenantModel):
    """N4: eventos de cobrança por crédito; alimentam p_cobrança e t_cobrança por réu."""

    __tablename__ = "collection_events"
    credit_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("credit_assets.id"), index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(40)
    )  # intimacao_523|deposito|sisbajud_pos|sisbajud_neg|impugnacao|alvara|levantamento
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    gross_amount: Mapped[float | None] = mapped_column(Float)
    withheld_amount: Mapped[float | None] = mapped_column(Float)  # IRRF/INSS
    net_amount: Mapped[float | None] = mapped_column(Float)
    bank_reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    publication_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("publications.id"))
    notes: Mapped[str | None] = mapped_column(Text)


class Portfolio(TenantModel):
    """N6: carteira / veículo."""

    __tablename__ = "portfolios"
    name: Mapped[str] = mapped_column(String(200))
    vehicle: Mapped[str | None] = mapped_column(String(40))  # pj|fidc|scd
    target_irr: Mapped[float | None] = mapped_column(Float)
    tax_rate: Mapped[float | None] = mapped_column(Float)
    committed_capital: Mapped[float | None] = mapped_column(Float)
    inception_date: Mapped[date | None] = mapped_column(Date)
    meta: Mapped[dict] = mapped_column(JSONType, default=dict)
    asset_count_cache: Mapped[int] = mapped_column(Integer, default=0)
