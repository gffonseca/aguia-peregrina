from __future__ import annotations

from pydantic import BaseModel, Field

DRAFT_PROMPT_VERSION = "minuta-v1"


class Citation(BaseModel):
    anchor: str
    document_page_id: str
    quote: str | None = None
    evidence_score: float = Field(ge=0, le=1)


class DraftOutput(BaseModel):
    body_markdown: str
    citations: list[Citation]
    confidence: float = Field(ge=0, le=1)
    thesis_codes_used: list[str]
    open_questions: list[str] = Field(default_factory=list)


def system_prompt(draft_type: str) -> str:
    return (
        f"Redija uma {draft_type} como SUGESTÃO para revisão por advogado inscrito. "
        "Use apenas as teses aprovadas fornecidas e os fatos do dossiê. Cada afirmação de fato "
        "deve citar um document_page_id. Marque incertezas em open_questions."
    )
