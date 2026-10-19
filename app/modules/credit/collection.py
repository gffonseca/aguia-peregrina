"""N4 — Cobrança / collection log.

Eventos por crédito alimentam `jm_collection` (p_cobrança e t_cobrança por réu).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.credit import CollectionEvent

EVENT_TYPES = (
    "intimacao_523",
    "deposito_voluntario",
    "sisbajud_positivo",
    "sisbajud_negativo",
    "impugnacao",
    "alvara",
    "levantamento",
    "acordo",
)


def log_event(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    credit_asset_id: uuid.UUID,
    event_type: str,
    occurred_at: datetime,
    gross_amount: float | None = None,
    withheld_amount: float | None = None,
    publication_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> CollectionEvent:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"evento inválido: {event_type}")
    net = None
    if gross_amount is not None:
        net = gross_amount - (withheld_amount or 0.0)
    ev = CollectionEvent(
        tenant_id=tenant_id,
        credit_asset_id=credit_asset_id,
        event_type=event_type,
        occurred_at=occurred_at,
        gross_amount=gross_amount,
        withheld_amount=withheld_amount,
        net_amount=net,
        publication_id=publication_id,
        notes=notes,
    )
    db.add(ev)
    return ev


def realized_cash(events: list[CollectionEvent]) -> float:
    return sum(e.net_amount or 0.0 for e in events if e.event_type == "levantamento")
