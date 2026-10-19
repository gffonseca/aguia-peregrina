from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, principal_in_tenant, tenant_id_dep
from app.core.security import Principal
from app.models.litigation import Case, Document
from app.modules.m02_autos.service import register_document
from app.schemas.litigation import DocumentOut
from app.workflows.engine import get_engine

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])


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
    if db.get(Case, case_id) is None:
        raise HTTPException(404, "processo não encontrado")
    content = await file.read()
    # TODO: enviar para S3; no esqueleto só registramos a chave lógica
    storage_key = f"{tenant_id}/{case_id}/{uuid.uuid4()}-{file.filename}"
    doc = register_document(
        db,
        tenant_id=tenant_id,
        case_id=case_id,
        storage_key=storage_key,
        filename=file.filename or "upload",
        content=content,
        mime_type=file.content_type,
        uploaded_by=principal.user_id,
    )
    db.commit()
    get_engine().dispatch(
        "process_document", {"tenant_id": str(tenant_id), "document_id": str(doc.id), "pages": []}
    )
    db.refresh(doc)
    return doc
