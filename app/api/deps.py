from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import Principal, decode_token, get_current_principal
from app.core.tenancy import current_tenant_id

DB = Depends(get_db)


def require_ops_key(x_ops_key: str | None = Header(default=None, alias="X-Ops-Key")) -> None:
    """Protege endpoints operacionais (mesma regra de POST /health/llm/ping):
    exige `X-Ops-Key == OPS_KEY`; sem OPS_KEY configurada ou chave errada → 404."""
    ops_key = get_settings().ops_key
    if not ops_key or not x_ops_key or not secrets.compare_digest(x_ops_key, ops_key):
        raise HTTPException(status.HTTP_404_NOT_FOUND)


@dataclass
class Operador:
    """Quem está agindo num endpoint operacional: pessoa logada (login + MFA) ou a chave de
    operação (integrações/admin). `email` vai para as trilhas de auditoria."""

    email: str
    via: str  # login | chave
    role: str | None = None


def require_operador(
    x_ops_key: str | None = Header(default=None, alias="X-Ops-Key"),
    authorization: str | None = Header(default=None),
    x_usuario: str | None = Header(default=None, alias="X-Usuario"),
) -> Operador:
    """Aceita a chave de operação OU um token de sessão com MFA do mesmo tenant do request.
    Sem nenhum dos dois → 404 (não revela que o endpoint existe)."""
    ops_key = get_settings().ops_key
    if ops_key and x_ops_key and secrets.compare_digest(x_ops_key, ops_key):
        return Operador(email=(x_usuario or "chave de operação")[:80], via="chave")
    if authorization and authorization.lower().startswith("bearer "):
        p = decode_token(authorization.split(" ", 1)[1], get_settings())
        if not p.mfa_verified:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "MFA obrigatório")
        tid = current_tenant_id.get()
        if tid is not None and tid != p.tenant_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "token de outro tenant")
        return Operador(email=(p.email or str(p.user_id))[:80], via="login", role=p.role)
    raise HTTPException(status.HTTP_404_NOT_FOUND)


def require_gestor(op: Operador = Depends(require_operador)) -> Operador:
    """Criar/desativar usuários: chave de operação ou sócio/admin logado."""
    if op.via == "chave" or op.role in ("admin", "partner"):
        return op
    raise HTTPException(status.HTTP_403_FORBIDDEN, "restrito a sócio/admin")


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


__all__ = [
    "DB",
    "Operador",
    "Session",
    "principal_in_tenant",
    "require_gestor",
    "require_operador",
    "require_ops_key",
    "tenant_id_dep",
]
