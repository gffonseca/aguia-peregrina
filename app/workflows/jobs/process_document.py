"""M2: OCR por visão LLM (stub) página a página + classificação de tipo de página."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.db import SessionLocal
from app.core.tenancy import current_tenant_id
from app.llm import get_llm_client
from app.models.litigation import Document
from app.modules.m02_autos.service import save_page


def ocr_page_stub(image_b64: str) -> tuple[str, str, float]:
    """Substituir por chamada de visão (claude-haiku) com prompt de OCR + tipo de página."""
    return ("", "outro", 0.0)


def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = uuid.UUID(payload["tenant_id"])
    token = current_tenant_id.set(tenant_id)
    try:
        with SessionLocal() as db:
            doc = db.get(Document, uuid.UUID(payload["document_id"]))
            if doc is None:
                return {"error": "document not found"}
            pages = payload.get("pages", [])  # [{"n": 1, "image_b64": "..."}]
            llm = get_llm_client()
            for p in pages:
                text, page_type, conf = ocr_page_stub(p.get("image_b64", ""))
                save_page(
                    db,
                    tenant_id=tenant_id,
                    document=doc,
                    page_number=p["n"],
                    text=text,
                    page_type=page_type,
                    ocr_model=llm.settings.llm_small_model,
                    confidence=conf,
                )
            doc.page_count = len(pages)
            doc.ocr_status = "done"
            db.commit()
            return {"document_id": str(doc.id), "pages": len(pages)}
    finally:
        current_tenant_id.reset(token)
