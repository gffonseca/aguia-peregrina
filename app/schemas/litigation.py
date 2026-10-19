from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CaseIn(BaseModel):
    cnj_number: str = Field(min_length=20, max_length=25)
    client_id: uuid.UUID | None = None
    court: str | None = None
    comarca: str | None = None
    typology: str | None = None
    side: str = "defense"
    phase: str | None = None
    claim_value: float | None = None
    filed_at: date | None = None
    external_ref: str | None = None


class CaseOut(ORMModel):
    id: uuid.UUID
    cnj_number: str
    court: str | None
    comarca: str | None
    typology: str | None
    side: str
    phase: str | None
    status: str
    created_at: datetime


class DocumentOut(ORMModel):
    id: uuid.UUID
    case_id: uuid.UUID
    filename: str
    kind: str | None
    page_count: int | None
    ocr_status: str


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
    status: str


class DraftOut(ORMModel):
    id: uuid.UUID
    case_id: uuid.UUID
    draft_type: str
    version: int
    body_markdown: str
    confidence: float | None
    status: str


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
