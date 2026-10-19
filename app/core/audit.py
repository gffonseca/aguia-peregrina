"""Trilha de auditoria.

Princípios (OAB / Res. CFOAB e ACP OAB-SP × Enter):
- toda peça tem advogado identificado (OAB) que a aprovou;
- nenhuma exportação sem `approved_at`;
- tempo mínimo de revisão por tipo de peça;
- revisor pode recusar com motivo;
- nenhum rótulo "fraudador" sem aprovação humana registrada.

`audit_log` é append-only (sem UPDATE/DELETE pela role da aplicação; ver migração).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def record(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    actor_oab: str | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    payload: dict[str, Any] | None = None,
) -> None:
    from app.models.audit import AuditLog

    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            actor_oab=actor_oab,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
            payload_hash=canonical_hash(payload or {}),
            created_at=datetime.now(UTC),
        )
    )
