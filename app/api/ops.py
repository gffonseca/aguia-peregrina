"""Endpoints operacionais (protegidos por `X-Ops-Key`, como /health/llm/ping).

- `POST /ops/bootstrap` (sem tenant): cria/garante tenant, advogado (OAB + MFA placeholder)
  e cliente. Idempotente por (tenant.name, tenant.kind), (user.email) e (client.name).
- `POST /ops/playbooks/load?file=<slug>` (com `X-Tenant-ID`): carrega um
  `playbooks/<slug>.playbook.yaml` do repositório em `theses`/`thesis_versions`; se o
  arquivo está `aprovado`, aprova a versão com a OAB e o timestamp do YAML.
- `GET /ops/cases/{case_id}/trace` (com `X-Tenant-ID`): llm_calls, audit_log, checagens de
  fraude e estado das peças — para verificação de ponta a ponta.

Nunca devolve segredos; a senha do usuário só entra, nunca sai.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import DB, require_ops_key, tenant_id_dep
from app.core.audit import record
from app.core.security import hash_password
from app.core.tenancy import TENANT_KINDS, current_tenant_id
from app.models.audit import AuditLog
from app.models.litigation import (
    Client,
    Document,
    DocumentPage,
    Dossier,
    Draft,
    DraftCitation,
    FraudCheck,
    LlmCall,
    Review,
)
from app.models.tenant import Tenant, User
from app.modules.m00_playbook.schema import PlaybookValidationError, load_playbook
from app.modules.m00_playbook.service import load_playbook_into_tenant, playbook_path

router = APIRouter(prefix="/ops", tags=["ops"], dependencies=[Depends(require_ops_key)])

OAB_PATTERN = r"^[A-Z]{2}\s?\d{1,6}[A-Z]?$"


class BootstrapLawyer(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    name: str
    oab: str = Field(pattern=OAB_PATTERN, description="formato 'PA 12724'")
    role: str = Field(default="partner", pattern="^(lawyer|partner)$")
    password: str = Field(min_length=12)


class BootstrapClient(BaseModel):
    name: str
    document: str | None = None
    erp_kind: str | None = None


class BootstrapIn(BaseModel):
    tenant_name: str
    tenant_kind: str = "law_firm"
    tenant_document: str | None = None
    tenant_settings: dict[str, Any] = Field(
        default_factory=dict,
        description="ex.: {'test_mode': true, 'review_min_seconds': {'contestacao': 30}}",
    )
    lawyer: BootstrapLawyer
    client: BootstrapClient | None = None


class BootstrapOut(BaseModel):
    tenant_id: uuid.UUID
    tenant_created: bool
    user_id: uuid.UUID
    user_created: bool
    client_id: uuid.UUID | None
    client_created: bool
    mfa_dev_code: str = "000000"


@router.get("/tenants")
def tenants(db: Session = DB) -> list[dict[str, Any]]:
    """Lista tenants (id, nome, tipo, ativo, test_mode) — sem segredos."""
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "kind": t.kind,
            "is_active": t.is_active,
            "test_mode": bool((t.settings or {}).get("test_mode")),
        }
        for t in db.scalars(select(Tenant).order_by(Tenant.created_at))
    ]


@router.post("/bootstrap", response_model=BootstrapOut)
def bootstrap(body: BootstrapIn, db: Session = DB) -> BootstrapOut:
    if body.tenant_kind not in TENANT_KINDS:
        raise HTTPException(422, f"tenant_kind deve ser um de {TENANT_KINDS}")
    tenant = db.scalar(
        select(Tenant).where(Tenant.name == body.tenant_name, Tenant.kind == body.tenant_kind)
    )
    tenant_created = tenant is None
    if tenant is None:
        tenant = Tenant(
            name=body.tenant_name,
            kind=body.tenant_kind,
            document=body.tenant_document,
            settings=body.tenant_settings,
        )
        db.add(tenant)
    elif body.tenant_settings:
        merged = dict(tenant.settings or {})
        merged.update(body.tenant_settings)
        tenant.settings = merged
    db.commit()

    # a partir daqui tudo tem tenant_id (users/clients estão sob RLS): fixa o contexto
    token = current_tenant_id.set(tenant.id)
    try:
        user = db.scalar(select(User).where(User.email == body.lawyer.email.lower()))
        user_created = user is None
        if user is None:
            user = User(
                tenant_id=tenant.id,
                email=body.lawyer.email.lower(),
                name=body.lawyer.name,
                role=body.lawyer.role,
                oab=body.lawyer.oab,
                password_hash=hash_password(body.lawyer.password),
                mfa_secret="placeholder-dev-000000",
                mfa_enabled=True,
            )
            db.add(user)
        else:
            user.name = body.lawyer.name
            user.role = body.lawyer.role
            user.oab = body.lawyer.oab
            user.password_hash = hash_password(body.lawyer.password)
            user.is_active = True
        db.flush()

        client_id, client_created = None, False
        if body.client is not None:
            client = db.scalar(select(Client).where(Client.name == body.client.name))
            client_created = client is None
            if client is None:
                client = Client(
                    tenant_id=tenant.id,
                    name=body.client.name,
                    document=body.client.document,
                    erp_kind=body.client.erp_kind,
                )
                db.add(client)
                db.flush()
            client_id = client.id
        record(
            db,
            tenant_id=tenant.id,
            actor_user_id=None,
            actor_oab=None,
            action="ops.bootstrap",
            entity_type="tenant",
            entity_id=tenant.id,
            payload={
                "tenant_created": tenant_created,
                "user_created": user_created,
                "user_email": user.email,
                "client_created": client_created,
                "settings_keys": sorted(body.tenant_settings),
            },
        )
        db.commit()
    finally:
        current_tenant_id.reset(token)
    return BootstrapOut(
        tenant_id=tenant.id,
        tenant_created=tenant_created,
        user_id=user.id,
        user_created=user_created,
        client_id=client_id,
        client_created=client_created,
    )


@router.post("/playbooks/load")
def playbooks_load(
    file: str = Query(description="slug do arquivo em playbooks/, ex.: consignado-rmc-tjpa"),
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> dict[str, Any]:
    path = playbook_path(file)
    if not path.exists():
        raise HTTPException(404, f"playbook não encontrado: {path.name}")
    try:
        pb = load_playbook(path)
    except PlaybookValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    author = db.scalar(select(User).where(User.oab == pb.metadata.autor_oab))
    approver = (
        db.scalar(select(User).where(User.oab == pb.metadata.aprovado_por_oab))
        if pb.metadata.aprovado_por_oab
        else None
    )
    if author is None:
        author = db.scalar(select(User).where(User.tenant_id == tenant_id).limit(1))
    if author is None:
        raise HTTPException(409, "tenant sem usuário para registrar a autoria; rode /ops/bootstrap")
    result = load_playbook_into_tenant(
        db,
        tenant_id=tenant_id,
        pb=pb,
        author_user_id=author.id,
        approver_user_id=approver.id if approver else None,
    )
    record(
        db,
        tenant_id=tenant_id,
        actor_user_id=approver.id if approver else None,
        actor_oab=pb.metadata.aprovado_por_oab,
        action="playbook.load",
        entity_type="playbook",
        entity_id=None,
        payload=result,
    )
    db.commit()
    return result


@router.get("/cases/{case_id}/trace")
def case_trace(
    case_id: uuid.UUID, db: Session = DB, tenant_id: uuid.UUID = Depends(tenant_id_dep)
) -> dict[str, Any]:
    calls = list(
        db.scalars(select(LlmCall).where(LlmCall.case_id == case_id).order_by(LlmCall.created_at))
    )
    checks = list(db.scalars(select(FraudCheck).where(FraudCheck.case_id == case_id)))
    drafts = list(db.scalars(select(Draft).where(Draft.case_id == case_id)))
    draft_ids = [d.id for d in drafts]
    reviews = (
        list(db.scalars(select(Review).where(Review.draft_id.in_(draft_ids)))) if draft_ids else []
    )
    n_cit = (
        db.scalar(select(func.count(DraftCitation.id)).where(DraftCitation.draft_id.in_(draft_ids)))
        if draft_ids
        else 0
    )
    entity_ids = {case_id, *draft_ids, *[c.id for c in checks]}
    entity_ids |= {d.id for d in db.scalars(select(Dossier).where(Dossier.case_id == case_id))}
    entity_ids |= {d.id for d in db.scalars(select(Document).where(Document.case_id == case_id))}
    audit = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id, AuditLog.entity_id.in_(list(entity_ids)))
            .order_by(AuditLog.created_at)
        )
    )
    n_pages = db.scalar(
        select(func.count(DocumentPage.id))
        .join(Document, Document.id == DocumentPage.document_id)
        .where(Document.case_id == case_id)
    )
    return {
        "case_id": str(case_id),
        "pages": int(n_pages or 0),
        "llm_calls": [
            {
                "id": str(c.id),
                "purpose": c.purpose,
                "model": c.model,
                "provider_model": c.provider_model,
                "prompt_version": c.prompt_version,
                "prompt_hash": c.prompt_hash,
                "input_tokens": c.input_tokens,
                "output_tokens": c.output_tokens,
                "latency_ms": c.latency_ms,
                "cost_usd": c.cost_usd,
                "status": c.status,
                "error": (c.error or "")[:200] or None,
                "created_at": c.created_at,
            }
            for c in calls
        ],
        "llm_totals": {
            "calls": len(calls),
            "input_tokens": sum(c.input_tokens or 0 for c in calls),
            "output_tokens": sum(c.output_tokens or 0 for c in calls),
            "cost_usd": round(sum(c.cost_usd or 0.0 for c in calls), 6),
        },
        "fraud_checks": [
            {
                "check_code": c.check_code,
                "result": c.result,
                "severity": c.severity,
                "human_decision": c.human_decision,
                "human_decision_by_oab": c.human_decision_by_oab,
            }
            for c in checks
        ],
        "fraud_labels_without_human_decision": [
            c.check_code
            for c in checks
            if c.human_decision is not None and not c.human_decision_by_oab
        ],
        "drafts": [
            {
                "id": str(d.id),
                "type": d.draft_type,
                "version": d.version,
                "status": d.status,
                "confidence": d.confidence,
                "thesis_versions": len(d.thesis_version_ids or []),
            }
            for d in drafts
        ],
        "draft_citations": int(n_cit or 0),
        "reviews": [
            {
                "id": str(r.id),
                "draft_id": str(r.draft_id),
                "reviewer_oab": r.reviewer_oab,
                "opened_at": r.opened_at,
                "approved_at": r.approved_at,
                "rejected_at": r.rejected_at,
                "decision": r.decision,
                "review_seconds": r.review_seconds,
            }
            for r in reviews
        ],
        "audit_log": [
            {
                "action": a.action,
                "entity_type": a.entity_type,
                "entity_id": str(a.entity_id) if a.entity_id else None,
                "actor_oab": a.actor_oab,
                "created_at": a.created_at,
                "payload_hash": a.payload_hash,
            }
            for a in audit
        ],
    }
