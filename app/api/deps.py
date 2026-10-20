from __future__ import annotations

import secrets
import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import Principal, get_current_principal
from app.core.tenancy import current_tenant_id

DB = Depends(get_db)


def require_ops_key(x_ops_key: str | None = Header(default=None, alias="X-Ops-Key")) -> None:
    """Protege endpoints operacionais (mesma regra de POST /health/llm/ping):
    exige `X-Ops-Key == OPS_KEY`; sem OPS_KEY configurada ou chave errada → 404."""
    ops_key = get_settings().ops_key
    if not ops_key or not x_ops_key or not secrets.compare_digest(x_ops_key, ops_key):
        raise HTTPException(status.HTTP_404_NOT_FOUND)


def tenant_id_dep() -> uuid.UUID:
    tid = current_tenant_id.get()
    if tid is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "tenant não resolvido")
    return tid


def principal_in_tenant(
    principal: Principal = Depends(get_current_principal),
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> Principal:
    if principal.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "token de outro tenant")
    return principal


__all__ = ["DB", "Session", "principal_in_tenant", "require_ops_key", "tenant_id_dep"]
