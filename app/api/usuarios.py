"""Usuários do escritório nos painéis. Criar/desativar: sócio/admin logado ou chave de operação.

- `GET  /usuarios`
- `POST /usuarios` `{email, nome, papel, oab?}` → link de convite (72 h) para a pessoa definir
  senha e autenticador. O sistema não envia e-mail: quem criou repassa o link.
- `POST /usuarios/{id}/convite` → novo convite (zera senha e autenticador; ex.: celular perdido).
- `POST /usuarios/{id}/desativar`
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, Operador, require_gestor, require_operador, tenant_id_dep
from app.core.config import get_settings
from app.core.security import Principal, issue_token
from app.models.tenant import User

router = APIRouter(prefix="/usuarios", tags=["usuarios"])
PAPEIS = ("partner", "lawyer", "paralegal", "analyst", "admin")
CONVITE_H = 72


class UsuarioIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    nome: str = Field(min_length=2, max_length=200)
    papel: str = Field(default="lawyer", pattern="^(partner|lawyer|paralegal|analyst|admin)$")
    oab: str | None = None


def _convite(u: User) -> dict[str, str]:
    p = Principal(u.id, u.tenant_id, u.role, u.oab, mfa_verified=False, email=u.email)
    tok = issue_token(p, get_settings(), ttl_seconds=CONVITE_H * 3600, finalidade="convite")
    return {
        "convite": tok,
        "link": f"/painel/entrar?convite={tok}",
        "validade_horas": str(CONVITE_H),
    }


def _out(u: User) -> dict[str, Any]:
    return {
        "id": str(u.id),
        "email": u.email,
        "nome": u.name,
        "papel": u.role,
        "oab": u.oab,
        "ativo": u.is_active,
        "autenticador": u.mfa_enabled,
        "ultimo_acesso": u.last_login_at.isoformat() if u.last_login_at else None,
    }


@router.get("")
def listar(
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
    _op: Operador = Depends(require_operador),
) -> list[dict[str, Any]]:
    # filtro explícito além do RLS do Postgres (defesa em profundidade)
    q = select(User).where(User.tenant_id == tenant_id).order_by(User.name)
    return [_out(u) for u in db.scalars(q)]


@router.post("")
def criar(
    body: UsuarioIn,
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
    _op: Operador = Depends(require_gestor),
) -> dict[str, Any]:
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email, User.tenant_id == tenant_id)):
        raise HTTPException(409, "já existe usuário com esse e-mail")
    u = User(
        tenant_id=tenant_id,
        email=email,
        name=body.nome,
        role=body.papel,
        oab=body.oab,
        password_hash=None,
        mfa_secret=None,
        mfa_enabled=False,
        is_active=True,
    )
    db.add(u)
    db.commit()
    return {**_out(u), **_convite(u)}


@router.post("/{uid}/convite")
def novo_convite(
    uid: uuid.UUID,
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
    _op: Operador = Depends(require_gestor),
) -> dict[str, Any]:
    u = db.get(User, uid)
    if u is None or u.tenant_id != tenant_id:
        raise HTTPException(404, "usuário não encontrado")
    u.password_hash, u.mfa_secret, u.mfa_enabled, u.is_active = None, None, False, True
    db.commit()
    return {**_out(u), **_convite(u)}


@router.post("/{uid}/desativar")
def desativar(
    uid: uuid.UUID,
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
    _op: Operador = Depends(require_gestor),
) -> dict[str, Any]:
    u = db.get(User, uid)
    if u is None or u.tenant_id != tenant_id:
        raise HTTPException(404, "usuário não encontrado")
    u.is_active = False
    db.commit()
    return _out(u)
