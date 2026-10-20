"""Lado defesa (M0–M11): clientes, processos, autos, teses, antifraude, dossiê, minuta, revisão."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import JSONType, TenantModel


class Client(TenantModel):
    """Cliente do escritório (réu de massa) ou, no credit_buyer, a própria operação."""

    __tablename__ = "clients"
    name: Mapped[str] = mapped_column(String(200))
    document: Mapped[str | None] = mapped_column(String(20))
    erp_kind: Mapped[str | None] = mapped_column(String(40))  # totvs|projuris|csv|api
    erp_config: Mapped[dict] = mapped_column(JSONType, default=dict)


class Case(TenantModel):
    __tablename__ = "cases"
    client_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("clients.id"))
    cnj_number: Mapped[str] = mapped_column(String(25), index=True)
    court: Mapped[str | None] = mapped_column(String(20))  # TJPA, TRT8...
    comarca: Mapped[str | None] = mapped_column(String(120))
    vara: Mapped[str | None] = mapped_column(String(120))
    typology: Mapped[str | None] = mapped_column(String(60))  # consignado|energia|voo|trabalhista
    # palpite determinístico (segmento CNJ + cliente + título) vindo de integrações;
    # a tipologia final é decidida pela classificação do M1
    typology_hint: Mapped[str | None] = mapped_column(String(60))
    side: Mapped[str] = mapped_column(String(10), default="defense")  # defense|plaintiff
    phase: Mapped[str | None] = mapped_column(
        String(40)
    )  # conhecimento|recurso|execucao|transitado
    claim_value: Mapped[float | None] = mapped_column(Float)
    filed_at: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="new")
    external_ref: Mapped[str | None] = mapped_column(String(120))  # id no ERP do cliente
    meta: Mapped[dict] = mapped_column(JSONType, default=dict)

    parties: Mapped[list[CaseParty]] = relationship(back_populates="case")


class CaseParty(TenantModel):
    __tablename__ = "case_parties"
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # autor|reu|advogado|terceiro
    name: Mapped[str] = mapped_column(String(300))
    document: Mapped[str | None] = mapped_column(String(20))
    oab: Mapped[str | None] = mapped_column(String(30))
    meta: Mapped[dict] = mapped_column(JSONType, default=dict)

    case: Mapped[Case] = relationship(back_populates="parties")


class Document(TenantModel):
    __tablename__ = "documents"
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    kind: Mapped[str | None] = mapped_column(String(60))  # inicial|procuracao|contrato|sentenca...
    storage_key: Mapped[str] = mapped_column(String(500))
    filename: Mapped[str] = mapped_column(String(300))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    sha256: Mapped[str | None] = mapped_column(String(64))
    page_count: Mapped[int | None] = mapped_column(Integer)
    ocr_status: Mapped[str] = mapped_column(String(20), default="pending")
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class DocumentPage(TenantModel):
    __tablename__ = "document_pages"
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documents.id"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str | None] = mapped_column(Text)
    page_type: Mapped[str | None] = mapped_column(String(60))  # classificado por LLM
    ocr_model: Mapped[str | None] = mapped_column(String(80))
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    # embedding pgvector é adicionado na migração (coluna `embedding vector(1536)`) só no PG


class Extraction(TenantModel):
    """Saída estruturada de LLM sobre um documento/caso (fatos, datas, valores)."""

    __tablename__ = "extractions"
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("documents.id"))
    schema_name: Mapped[str] = mapped_column(String(80))
    schema_version: Mapped[str] = mapped_column(String(20))
    data: Mapped[dict] = mapped_column(JSONType, default=dict)
    llm_call_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    confidence: Mapped[float | None] = mapped_column(Float)


class Thesis(TenantModel):
    """M0 Playbook: árvore de teses por tipologia, versionada e aprovada por sócio."""

    __tablename__ = "theses"
    typology: Mapped[str] = mapped_column(String(60), index=True)
    code: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(300))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("theses.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class ThesisVersion(TenantModel):
    __tablename__ = "thesis_versions"
    thesis_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("theses.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    body_markdown: Mapped[str] = mapped_column(Text)
    conditions: Mapped[dict] = mapped_column(JSONType, default=dict)  # condições de exceção
    template_ref: Mapped[str | None] = mapped_column(String(200))
    author_user_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    author_oab: Mapped[str] = mapped_column(String(30))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    approved_by_oab: Mapped[str | None] = mapped_column(String(30))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FraudCheck(TenantModel):
    """M4: checagem determinística. Nunca produz rótulo 'fraudador' sozinha."""

    __tablename__ = "fraud_checks"
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    check_code: Mapped[str] = mapped_column(String(60))  # oab_invalida|procuracao_ausente|...
    result: Mapped[str] = mapped_column(String(20))  # pass|flag|error
    evidence: Mapped[dict] = mapped_column(JSONType, default=dict)
    severity: Mapped[str] = mapped_column(String(10), default="info")
    human_decision: Mapped[str | None] = mapped_column(String(20))  # confirmed|dismissed
    human_decision_by_oab: Mapped[str | None] = mapped_column(String(30))
    human_decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Dossier(TenantModel):
    """M5: documento consolidado do caso antes de qualquer redação."""

    __tablename__ = "dossiers"
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[dict] = mapped_column(
        JSONType, default=dict
    )  # fatos, timeline, provas, exposição
    exposure_estimate: Mapped[float | None] = mapped_column(Float)
    llm_call_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(20), default="draft")


class Draft(TenantModel):
    """M6: minuta como sugestão, com citações e score."""

    __tablename__ = "drafts"
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    dossier_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("dossiers.id"))
    draft_type: Mapped[str] = mapped_column(String(40))  # contestacao|recurso|manifestacao
    version: Mapped[int] = mapped_column(Integer, default=1)
    body_markdown: Mapped[str] = mapped_column(Text)
    thesis_version_ids: Mapped[list] = mapped_column(JSONType, default=list)
    confidence: Mapped[float | None] = mapped_column(Float)
    llm_call_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(
        String(20), default="generated"
    )  # generated|in_review|approved|rejected|exported


class DraftCitation(TenantModel):
    __tablename__ = "draft_citations"
    draft_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("drafts.id"), index=True)
    document_page_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("document_pages.id"))
    quote: Mapped[str | None] = mapped_column(Text)
    anchor: Mapped[str | None] = mapped_column(String(120))  # trecho da minuta que cita
    evidence_score: Mapped[float | None] = mapped_column(Float)


class Review(TenantModel):
    """M7: revisão por advogado. Export só após approved_at e tempo mínimo."""

    __tablename__ = "reviews"
    draft_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("drafts.id"), index=True)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    reviewer_oab: Mapped[str] = mapped_column(String(30))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision: Mapped[str | None] = mapped_column(String(20))  # approved|rejected|changes_requested
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    diff: Mapped[str | None] = mapped_column(Text)
    review_seconds: Mapped[int | None] = mapped_column(Integer)
    substantial_change: Mapped[bool | None] = mapped_column(Boolean)


class Filing(TenantModel):
    """M8: protocolo humano com recibo."""

    __tablename__ = "filings"
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    draft_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("drafts.id"))
    review_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("reviews.id"))
    filed_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    filed_by_oab: Mapped[str] = mapped_column(String(30))
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    receipt_storage_key: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="filed")


class Publication(TenantModel):
    """M1/M9: publicação/intimação capturada do provedor."""

    __tablename__ = "publications"
    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    provider_ref: Mapped[str | None] = mapped_column(String(200), index=True)
    cnj_number: Mapped[str | None] = mapped_column(String(25), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_text: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(40))  # despacho|sentenca|liminar|prazo
    summary: Mapped[str | None] = mapped_column(Text)
    deadline_at: Mapped[date | None] = mapped_column(Date)
    alert_level: Mapped[str | None] = mapped_column(String(10))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Outcome(TenantModel):
    """M10: resultado do processo para write-back e jurimetria."""

    __tablename__ = "outcomes"
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    stage: Mapped[str] = mapped_column(String(30))  # 1g|2g|superior|execucao
    result: Mapped[str] = mapped_column(
        String(40)
    )  # procedente|parcial|improcedente|acordo|extinto
    award_value: Mapped[float | None] = mapped_column(Float)
    decided_at: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(Text)
    thesis_version_ids: Mapped[list] = mapped_column(JSONType, default=list)


class ErpWriteback(TenantModel):
    __tablename__ = "erp_writebacks"
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    connector: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LlmCall(TenantModel):
    """Transversal: toda chamada a LLM. Nunca grava o prompt em claro, só o hash."""

    __tablename__ = "llm_calls"
    purpose: Mapped[str] = mapped_column(String(60), index=True)
    model: Mapped[str] = mapped_column(String(80))
    provider_model: Mapped[str | None] = mapped_column(String(120))
    prompt_hash: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="ok")
    error: Mapped[str | None] = mapped_column(Text)
    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    meta: Mapped[dict] = mapped_column(JSONType, default=dict)


class GtTask(TenantModel):
    """M11: ground truth — modelo × revisor × revisor sênior."""

    __tablename__ = "gt_tasks"
    entity_type: Mapped[str] = mapped_column(String(40))  # draft|extraction|fraud_check|dossier
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    model_answer: Mapped[dict] = mapped_column(JSONType, default=dict)
    reviewer_answer: Mapped[dict | None] = mapped_column(JSONType)
    senior_answer: Mapped[dict | None] = mapped_column(JSONType)
    reviewer_oab: Mapped[str | None] = mapped_column(String(30))
    senior_oab: Mapped[str | None] = mapped_column(String(30))
    agreement_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="open")
