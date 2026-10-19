from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import Principal, get_current_principal
from app.core.tenancy import current_tenant_id

DB = Depends(get_db)


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


__all__ = ["DB", "Session", "principal_in_tenant", "tenant_id_dep"]
