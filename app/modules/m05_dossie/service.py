from __future__ import annotations

from pydantic import BaseModel, Field

DOSSIER_PROMPT_VERSION = "dossie-v1"


class Evidence(BaseModel):
    description: str
    document_page_ids: list[str] = Field(default_factory=list)
    score: float = Field(ge=0, le=1)


class TimelineEvent(BaseModel):
    date: str
    event: str
    source_page_ids: list[str] = Field(default_factory=list)


class DossierContent(BaseModel):
    """Schema de saída estruturada do LLM (structured output)."""

    facts: list[str]
    timeline: list[TimelineEvent]
    evidences: list[Evidence]
    claims: list[str]
    weaknesses: list[str]
    applicable_theses: list[str]
    exposure_estimate: float | None = None
    exposure_basis: str | None = None


def system_prompt() -> str:
    return (
        "Você é um analista jurídico. Consolide os autos em um dossiê estruturado. "
        "Cite sempre o document_page_id de cada fato e prova. Não invente fatos. "
        "Não classifique pessoas; aponte apenas indícios com a fonte."
    )
