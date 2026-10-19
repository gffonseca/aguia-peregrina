from __future__ import annotations

from pydantic import BaseModel, Field

CATEGORIES = ("despacho", "decisao", "liminar", "sentenca", "acordao", "intimacao_prazo", "outro")


class PublicationSummary(BaseModel):
    category: str
    summary: str
    deadline_days: int | None = None
    alert_level: str = Field(default="info", pattern="^(info|warn|urgent)$")
    milestone: str | None = None  # para créditos: intimacao_523|deposito|alvara…


def alert_level_for(category: str, deadline_days: int | None) -> str:
    if category == "liminar" or (deadline_days is not None and deadline_days <= 2):
        return "urgent"
    if deadline_days is not None and deadline_days <= 5:
        return "warn"
    return "info"
