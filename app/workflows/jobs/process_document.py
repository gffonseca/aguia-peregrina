"""M2: grava o texto de cada página e classifica o tipo de página (modelo pequeno).

Payload: `{"tenant_id", "document_id", "pages": [{"n": 1, "text": "..."}]}`. O texto é
extraído no upload (PDF com camada de texto ou texto puro); páginas sem texto ficam com
`page_type=outro` e `ocr_confidence=0` até o OCR por visão existir.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.core.db import SessionLocal
from app.core.tenancy import current_tenant_id
from app.llm import get_llm_client
from app.models.litigation import Document
from app.modules.m02_autos.service import (
    CLASSIFY_PROMPT_VERSION,
    MAX_CHARS_PER_PAGE_FOR_CLASSIFICATION,
    PAGE_TYPES,
    DocumentClassification,
    classification_system_prompt,
    dominant_kind,
    save_page,
)

log = logging.getLogger(__name__)


def _classify(
    db: Any, *, tenant_id: uuid.UUID, doc: Document, pages: list[dict[str, Any]]
) -> tuple[dict[int, tuple[str, float]], str | None]:
    llm = get_llm_client()
    excerpts = []
    for p in pages:
        text = (p.get("text") or "").strip()
        if not text:
            continue
        excerpts.append(f"### Página {p['n']}\n{text[:MAX_CHARS_PER_PAGE_FOR_CLASSIFICATION]}")
    if not excerpts:
        return {}, None
    user = f"Arquivo: {doc.filename}\nTotal de páginas: {len(pages)}\n\n" + "\n\n".join(excerpts)
    try:
        out, _ = llm.structured(
            [
                {"role": "system", "content": classification_system_prompt()},
                {"role": "user", "content": user},
            ],
            DocumentClassification,
            purpose="m2.classify_pages",
            db=db,
            tenant_id=tenant_id,
            case_id=doc.case_id,
            model=llm.settings.llm_small_model,
            prompt_version=CLASSIFY_PROMPT_VERSION,
            temperature=0,
        )
    except ValueError as exc:
        log.warning("classificação de páginas falhou para %s: %s", doc.id, exc)
        return {}, None
    mapping = {pc.page_number: (pc.page_type, pc.confidence) for pc in out.pages}
    return mapping, out.document_kind


def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = uuid.UUID(payload["tenant_id"])
    token = current_tenant_id.set(tenant_id)
    try:
        with SessionLocal() as db:
            doc = db.get(Document, uuid.UUID(payload["document_id"]))
            if doc is None:
                return {"error": "document not found"}
            pages: list[dict[str, Any]] = payload.get("pages", [])
            llm = get_llm_client()
            classes, kind = _classify(db, tenant_id=tenant_id, doc=doc, pages=pages)
            types: list[str] = []
            for p in pages:
                text = p.get("text") or ""
                page_type, conf = classes.get(int(p["n"]), ("outro", 0.0))
                if not text.strip():
                    page_type, conf = "outro", 0.0
                types.append(page_type)
                save_page(
                    db,
                    tenant_id=tenant_id,
                    document=doc,
                    page_number=int(p["n"]),
                    text=text,
                    page_type=page_type,
                    ocr_model=llm.settings.llm_small_model,
                    confidence=conf,
                )
            doc.page_count = len(pages)
            doc.kind = kind if kind in PAGE_TYPES else dominant_kind(types)
            doc.ocr_status = (
                "done" if all((p.get("text") or "").strip() for p in pages) else ("partial")
            )
            db.commit()
            return {
                "document_id": str(doc.id),
                "pages": len(pages),
                "kind": doc.kind,
                "page_types": types,
            }
    finally:
        current_tenant_id.reset(token)
