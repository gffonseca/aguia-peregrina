from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, principal_in_tenant, tenant_id_dep
from app.core.audit import record
from app.core.security import Principal
from app.models.litigation import Case, Document, DocumentPage
from app.modules.m02_autos.service import extract_pages, register_document
from app.schemas.litigation import DocumentOut, DocumentPageOut
from app.workflows.engine import get_engine

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.get("", response_model=list[DocumentOut])
def list_documents(
    case_id: uuid.UUID, db: Session = DB, _: Principal = Depends(principal_in_tenant)
) -> list[Document]:
    return list(db.scalars(select(Document).where(Document.case_id == case_id)))


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    case_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = DB,
    principal: Principal = Depends(principal_in_tenant),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> Document:
    """Registra o arquivo, extrai o texto por página e dispara `process_document` (M2).

    Idempotente por (case_id, sha256): reenviar o mesmo arquivo devolve o documento existente.
    """
    if db.get(Case, case_id) is None:
        raise HTTPException(404, "processo não encontrado")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "arquivo acima de 25 MB")
    if not content:
        raise HTTPException(422, "arquivo vazio")
    import hashlib

    sha = hashlib.sha256(content).hexdigest()
    existing = db.scalar(
        select(Document).where(Document.case_id == case_id, Document.sha256 == sha)
    )
    if existing is not None:
        return existing
    filename = file.filename or "upload"
    try:
        pages = extract_pages(content, mime_type=file.content_type, filename=filename)
    except Exception as exc:  # noqa: BLE001 - PDF corrompido etc.
        raise HTTPException(422, f"não foi possível extrair texto: {exc}") from exc
    # mesmo nome e mesmo texto por página (ex.: PDF regenerado com outro timestamp) → reuso
    for other in db.scalars(
        select(Document).where(Document.case_id == case_id, Document.filename == filename)
    ):
        texts = [
            t or ""
            for t in db.scalars(
                select(DocumentPage.text)
                .where(DocumentPage.document_id == other.id)
                .order_by(DocumentPage.page_number)
            )
        ]
        if texts and [t.strip() for t in texts] == [p.strip() for p in pages]:
            return other
    # TODO: enviar para S3; no esqueleto só registramos a chave lógica
    storage_key = f"{tenant_id}/{case_id}/{uuid.uuid4()}-{filename}"
    doc = register_document(
        db,
        tenant_id=tenant_id,
        case_id=case_id,
        storage_key=storage_key,
        filename=filename,
        content=content,
        mime_type=file.content_type,
        uploaded_by=principal.user_id,
    )
    db.flush()
    record(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal.user_id,
        actor_oab=principal.oab,
        action="document.upload",
        entity_type="document",
        entity_id=doc.id,
        payload={"filename": filename, "sha256": sha, "pages": len(pages)},
    )
    db.commit()
    get_engine().dispatch(
        "process_document",
        {
            "tenant_id": str(tenant_id),
            "document_id": str(doc.id),
            "pages": [{"n": i + 1, "text": t} for i, t in enumerate(pages)],
        },
    )
    db.refresh(doc)
    return doc


@router.get("/{document_id}/pages", response_model=list[DocumentPageOut])
def list_pages(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = DB,
    _: Principal = Depends(principal_in_tenant),
) -> list[DocumentPage]:
    doc = db.get(Document, document_id)
    if doc is None or doc.case_id != case_id:
        raise HTTPException(404, "documento não encontrado")
    return list(
        db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
        )
    )
