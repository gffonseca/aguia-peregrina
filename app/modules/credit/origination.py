"""N1 — Originação / CRM de cedentes.

Regras fixas:
- lista de exclusão (muralha): nenhum cliente do tenant `law_firm` pode virar cedente em um
  tenant `credit_buyer`; a checagem roda contra `exclusions` (hash de CPF/CNPJ) antes do contato;
- registro de base legal LGPD, origem do lead e opt-out;
- nenhum texto de abordagem que prometa êxito.
"""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy.orm import Session

from app.models.credit import Cedente

FUNNEL = ("candidate", "contacted", "documents", "proposal", "signed", "lost")


def document_fingerprint(document: str) -> str:
    digits = "".join(ch for ch in document if ch.isdigit())
    return hashlib.sha256(digits.encode()).hexdigest()


def is_excluded(document: str, exclusion_hashes: set[str]) -> bool:
    return document_fingerprint(document) in exclusion_hashes


def create_lead(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    name: str,
    document: str | None,
    lead_source: str,
    lgpd_basis: str,
    exclusion_hashes: set[str] | None = None,
) -> Cedente:
    excluded_reason = None
    if document and exclusion_hashes and is_excluded(document, exclusion_hashes):
        excluded_reason = "lista de exclusão (muralha de dados)"
    lead = Cedente(
        tenant_id=tenant_id,
        name=name,
        document=document,
        lead_source=lead_source,
        lgpd_basis=lgpd_basis,
        excluded_reason=excluded_reason,
        funnel_stage="lost" if excluded_reason else "candidate",
    )
    db.add(lead)
    return lead


def advance(lead: Cedente, stage: str) -> Cedente:
    if stage not in FUNNEL:
        raise ValueError(f"estágio inválido: {stage}")
    if lead.excluded_reason or lead.opted_out:
        raise PermissionError("lead excluído ou com opt-out")
    lead.funnel_stage = stage
    return lead
