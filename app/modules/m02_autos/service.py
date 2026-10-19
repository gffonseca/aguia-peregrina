from __future__ import annotations

import hashlib
import uuid

from sqlalchemy.orm import Session

from app.models.litigation import Document, DocumentPage

PAGE_TYPES = (
    "peticao_inicial",
    "procuracao",
    "documento_pessoal",
    "comprovante_endereco",
    "contrato",
    "extrato",
    "decisao",
    "sentenca",
    "acordao",
    "calculo",
    "alvara",
    "outro",
)


def register_document(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    case_id: uuid.UUID,
    storage_key: str,
    filename: str,
    content: bytes | None,
    mime_type: str | None,
    uploaded_by: uuid.UUID | None,
) -> Document:
    doc = Document(
        tenant_id=tenant_id,
        case_id=case_id,
        storage_key=storage_key,
        filename=filename,
        mime_type=mime_type,
        sha256=hashlib.sha256(content).hexdigest() if content else None,
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    return doc


def save_page(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    document: Document,
    page_number: int,
    text: str,
    page_type: str,
    ocr_model: str,
    confidence: float | None,
) -> DocumentPage:
    if page_type not in PAGE_TYPES:
        page_type = "outro"
    page = DocumentPage(
        tenant_id=tenant_id,
        document_id=document.id,
        page_number=page_number,
        text=text,
        page_type=page_type,
        ocr_model=ocr_model,
        ocr_confidence=confidence,
    )
    db.add(page)
    return page
