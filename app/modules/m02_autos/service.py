"""M2 Autos — upload, extração de texto por página, classificação de tipo de página.

Extração: PDF com camada de texto → `pypdf`; texto puro/markdown → páginas separadas por
form-feed (`\\f`) ou por marcadores `--- página N ---`. Páginas sem texto (digitalizadas)
ficam vazias e marcadas para OCR por visão (não implementado neste passo; ver README).
Classificação: um chamado ao modelo pequeno por documento (saída estruturada, em português).
"""

from __future__ import annotations

import hashlib
import io
import re
import uuid

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.litigation import Document, DocumentPage

PAGE_TYPES = (
    "peticao_inicial",
    "procuracao",
    "documento_pessoal",
    "comprovante_endereco",
    "contrato",
    "extrato",
    "extrato_beneficio",
    "comprovante_ted",
    "log_autenticacao",
    "biometria",
    "fatura_cartao",
    "decisao",
    "sentenca",
    "acordao",
    "calculo",
    "alvara",
    "outro",
)

# tipos de página → tipos de prova do playbook / checklist do M3
PAGE_TYPE_TO_EVIDENCE_KIND: dict[str, set[str]] = {
    "contrato": {"contrato"},
    "extrato": {"extrato", "extrato_bancario"},
    "extrato_beneficio": {"extrato_beneficio", "extrato"},
    "comprovante_ted": {"comprovante_ted", "comprovante_credito"},
    "log_autenticacao": {"log_autenticacao"},
    "biometria": {"biometria"},
    "fatura_cartao": {"fatura_cartao"},
    "documento_pessoal": {"documento_pessoal", "documento_identidade"},
    "procuracao": {"procuracao"},
    "comprovante_endereco": {"comprovante_endereco"},
    "peticao_inicial": {"peticao_inicial"},
}

CLASSIFY_PROMPT_VERSION = "m2-classifica-paginas-v1"
MAX_CHARS_PER_PAGE_FOR_CLASSIFICATION = 700

_PAGE_MARKER = re.compile(r"^\s*-{3,}\s*p[áa]gina\s+\d+\s*-{3,}\s*$", re.IGNORECASE | re.MULTILINE)


class PageClassification(BaseModel):
    page_number: int = Field(ge=1)
    page_type: str
    confidence: float = Field(ge=0, le=1)


class DocumentClassification(BaseModel):
    """Saída estruturada do modelo pequeno: um item por página."""

    document_kind: str = Field(description="tipo predominante do documento (um dos page_types)")
    pages: list[PageClassification]


def classification_system_prompt() -> str:
    tipos = ", ".join(PAGE_TYPES)
    return (
        "Você classifica páginas de autos judiciais e de subsídios de defesa em processos cíveis "
        "brasileiros. Para cada página, escolha exatamente um tipo dentre: "
        f"{tipos}. Use 'peticao_inicial' para todas as páginas da inicial (inclusive pedidos e "
        "valor da causa); 'procuracao' para a procuração; 'comprovante_endereco' para contas de "
        "consumo/boletos usados como prova de residência; 'contrato' para CCB, cédula, termo de "
        "adesão ou proposta; 'comprovante_ted' para TED/PIX/ordem de pagamento; "
        "'log_autenticacao' para registros de IP, dispositivo, selfie, geolocalização e "
        "assinatura eletrônica; 'extrato_beneficio' para histórico de consignações do INSS. "
        "Não invente páginas; devolva uma entrada por página recebida, com confiança 0–1. "
        "Responda apenas com o JSON pedido."
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


def is_pdf(content: bytes, mime_type: str | None, filename: str) -> bool:
    return (
        content[:5] == b"%PDF-"
        or (mime_type or "") == "application/pdf"
        or (filename.lower().endswith(".pdf"))
    )


def extract_pages(content: bytes, *, mime_type: str | None, filename: str) -> list[str]:
    """Devolve o texto de cada página (lista indexada a partir da página 1)."""
    if is_pdf(content, mime_type, filename):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return [(p.extract_text() or "").strip() for p in reader.pages]
    text = content.decode("utf-8", errors="replace")
    if "\f" in text:
        parts = text.split("\f")
    elif _PAGE_MARKER.search(text):
        parts = _PAGE_MARKER.split(text)
    else:
        parts = [text]
    pages = [p.strip() for p in parts]
    pages = [p for p in pages if p] or [""]
    return pages


def dominant_kind(page_types: list[str]) -> str | None:
    if not page_types:
        return None
    counts: dict[str, int] = {}
    for t in page_types:
        counts[t] = counts.get(t, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def evidence_kinds_from_page_types(page_types: list[str]) -> set[str]:
    out: set[str] = set()
    for t in page_types:
        out |= PAGE_TYPE_TO_EVIDENCE_KIND.get(t, set())
    return out


__all__ = [
    "CLASSIFY_PROMPT_VERSION",
    "MAX_CHARS_PER_PAGE_FOR_CLASSIFICATION",
    "PAGE_TYPES",
    "DocumentClassification",
    "classification_system_prompt",
    "dominant_kind",
    "evidence_kinds_from_page_types",
    "extract_pages",
    "is_pdf",
    "register_document",
    "save_page",
]
