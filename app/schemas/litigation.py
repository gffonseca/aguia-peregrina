from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CasePartyIn(BaseModel):
    role: str = Field(pattern="^(autor|reu|advogado|advogado_contrario|terceiro)$")
    name: str = Field(min_length=2, max_length=300)
    document: str | None = Field(default=None, max_length=20)
    oab: str | None = Field(default=None, max_length=30)
    meta: dict = Field(default_factory=dict)


class CasePartyOut(ORMModel):
    id: uuid.UUID
    role: str
    name: str
    document: str | None
    oab: str | None


class CaseIn(BaseModel):
    cnj_number: str = Field(min_length=20, max_length=25)
    client_id: uuid.UUID | None = None
    court: str | None = None
    comarca: str | None = None
    vara: str | None = None
    typology: str | None = None
    side: str = "defense"
    phase: str | None = None
    claim_value: float | None = None
    filed_at: date | None = None
    external_ref: str | None = None
    parties: list[CasePartyIn] = Field(default_factory=list)


class CaseOut(ORMModel):
    id: uuid.UUID
    cnj_number: str
    client_id: uuid.UUID | None
    court: str | None
    comarca: str | None
    vara: str | None
    typology: str | None
    side: str
    phase: str | None
    claim_value: float | None
    filed_at: date | None
    status: str
    external_ref: str | None
    created_at: datetime
    parties: list[CasePartyOut] = Field(default_factory=list)


class DocumentOut(ORMModel):
    id: uuid.UUID
    case_id: uuid.UUID
    filename: str
    kind: str | None
    page_count: int | None
    ocr_status: str


class DocumentPageOut(ORMModel):
    id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    page_type: str | None
    ocr_confidence: float | None
    text: str | None


class ThesisIn(BaseModel):
    typology: str
    code: str
    title: str
    parent_id: uuid.UUID | None = None


class ThesisVersionIn(BaseModel):
    body_markdown: str
    conditions: dict = Field(default_factory=dict)


class ThesisOut(ORMModel):
    id: uuid.UUID
    typology: str
    code: str
    title: str
    is_active: bool
    current_version_id: uuid.UUID | None


class FraudCheckOut(ORMModel):
    id: uuid.UUID
    check_code: str
    result: str
    severity: str
    evidence: dict
    human_decision: str | None
    human_decision_by_oab: str | None


class FraudDecisionIn(BaseModel):
    decision: str = Field(pattern="^(confirmed|dismissed)$")


class DossierOut(ORMModel):
    id: uuid.UUID
    case_id: uuid.UUID
    version: int
    content: dict
    exposure_estimate: float | None
    llm_call_id: uuid.UUID | None
    status: str


class DraftCitationOut(ORMModel):
    id: uuid.UUID
    document_page_id: uuid.UUID
    anchor: str | None
    quote: str | None
    evidence_score: float | None


class DraftOut(ORMModel):
    id: uuid.UUID
    case_id: uuid.UUID
    dossier_id: uuid.UUID | None
    draft_type: str
    version: int
    body_markdown: str
    thesis_version_ids: list
    confidence: float | None
    llm_call_id: uuid.UUID | None
    status: str
    citations: list[DraftCitationOut] = Field(default_factory=list)


class DraftGenerateIn(BaseModel):
    draft_type: str = "contestacao"
    dossier_id: uuid.UUID | None = None
    context: str = ""


class ReviewOut(ORMModel):
    id: uuid.UUID
    draft_id: uuid.UUID
    reviewer_oab: str
    opened_at: datetime
    approved_at: datetime | None
    rejected_at: datetime | None
    decision: str | None
    rejection_reason: str | None
    review_seconds: int | None


class RejectIn(BaseModel):
    reason: str = Field(min_length=10)


class PublicationOut(ORMModel):
    id: uuid.UUID
    case_id: uuid.UUID | None
    provider: str
    cnj_number: str | None
    category: str | None
    summary: str | None
    deadline_at: date | None
    alert_level: str | None
