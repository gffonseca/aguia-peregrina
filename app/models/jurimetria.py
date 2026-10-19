"""As cinco tabelas de jurimetria. Chave: tese × tribunal × comarca/vara × réu × ano."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JSONType, TenantModel


class _JmKey:
    thesis_code: Mapped[str | None] = mapped_column(String(60), index=True)
    typology: Mapped[str | None] = mapped_column(String(60), index=True)
    court: Mapped[str | None] = mapped_column(String(20), index=True)
    comarca: Mapped[str | None] = mapped_column(String(120))
    organ: Mapped[str | None] = mapped_column(String(120))  # vara / turma / câmara
    debtor_document: Mapped[str | None] = mapped_column(String(20), index=True)
    filing_year: Mapped[int | None] = mapped_column(Integer)
    n: Mapped[int] = mapped_column(Integer, default=0)  # tamanho da amostra (prior se n < 30)
    source: Mapped[str | None] = mapped_column(String(40))  # datajud|djen|propria|cnj_prior
    as_of: Mapped[date | None] = mapped_column(Date)


class JmOutcome(_JmKey, TenantModel):
    """(1) P(acordo), P(procedência total/parcial/improcedência), P(extinção sem mérito)."""

    __tablename__ = "jm_outcome"
    p_settlement: Mapped[float | None] = mapped_column(Float)
    p_granted_full: Mapped[float | None] = mapped_column(Float)
    p_granted_partial: Mapped[float | None] = mapped_column(Float)
    p_denied: Mapped[float | None] = mapped_column(Float)
    p_dismissed: Mapped[float | None] = mapped_column(Float)  # inclui Tema 1.198


class JmAward(_JmKey, TenantModel):
    """(2) Distribuição da condenação por tese (não vem do DataJud; NLP do dispositivo)."""

    __tablename__ = "jm_award"
    award_p25: Mapped[float | None] = mapped_column(Float)
    award_median: Mapped[float | None] = mapped_column(Float)
    award_p75: Mapped[float | None] = mapped_column(Float)
    award_over_claim: Mapped[float | None] = mapped_column(Float)


class JmDuration(_JmKey, TenantModel):
    """(3) Tempos entre marcos (Kaplan–Meier/Cox; CNJ como prior)."""

    __tablename__ = "jm_duration"
    milestone_from: Mapped[str] = mapped_column(String(40))
    milestone_to: Mapped[str] = mapped_column(String(40))
    months_p10: Mapped[float | None] = mapped_column(Float)
    months_median: Mapped[float | None] = mapped_column(Float)
    months_p90: Mapped[float | None] = mapped_column(Float)
    censored_share: Mapped[float | None] = mapped_column(Float)


class JmReversal(_JmKey, TenantModel):
    """(4) P(provimento total/parcial) do recurso por órgão."""

    __tablename__ = "jm_reversal"
    appellant: Mapped[str] = mapped_column(String(10))  # reu|autor
    p_reversed_full: Mapped[float | None] = mapped_column(Float)
    p_reversed_partial: Mapped[float | None] = mapped_column(Float)
    avg_reduction: Mapped[float | None] = mapped_column(Float)


class JmCollection(_JmKey, TenantModel):
    """(5) Comportamento de pagamento por réu (dados próprios do collection log)."""

    __tablename__ = "jm_collection"
    p_voluntary_15d: Mapped[float | None] = mapped_column(Float)
    p_sisbajud_positive: Mapped[float | None] = mapped_column(Float)
    p_collected: Mapped[float | None] = mapped_column(Float)
    months_to_cash_median: Mapped[float | None] = mapped_column(Float)
    details: Mapped[dict] = mapped_column(JSONType, default=dict)
