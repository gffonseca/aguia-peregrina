"""Login individual: e-mail + senha + código do app autenticador (TOTP).

Fluxo de quem entra pela primeira vez (convite):
1. A coordenação cria o usuário (POST /ops/usuarios) e recebe um link de convite (72 h).
2. A pessoa abre /painel/entrar?convite=..., define a senha (POST /auth/convite/senha) e
   recebe o QR do autenticador.
3. Confirma um código (POST /auth/convite/confirmar) → MFA ativo; daí em diante só entra com
   senha + código.

Em dev/test, usuário sem TOTP ainda aceita o código fixo 000000 (testes e piloto local); em
staging/prod nunca.
"""

from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import totp
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.security import (
    MFAPlaceholder,
    Principal,
    decode_token,
    hash_password,
    issue_token,
    verify_password,
)
from app.core.tenancy import current_tenant_id
from app.models.tenant import Tenant, User
from app.schemas.auth import LoginIn, MfaIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])

_FALHAS: dict[str, deque[float]] = defaultdict(deque)
MAX_FALHAS, JANELA_S = 6, 15 * 60
SENHA_MIN = 12


def _bloqueado(chave: str) -> bool:
    q = _FALHAS[chave]
    while q and q[0] < time.time() - JANELA_S:
        q.popleft()
    return len(q) >= MAX_FALHAS


def _falhou(chave: str) -> None:
    _FALHAS[chave].append(time.time())


def _usuario(db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
    token = current_tenant_id.set(tenant_id)
    try:
        return db.get(User, user_id)
    finally:
        current_tenant_id.reset(token)


@router.get("/tenant")
def tenant_padrao(db: Session = Depends(get_db)) -> dict[str, str]:
    """Tenant do escritório para a tela de login dos painéis (não é segredo)."""
    nome = get_settings().motor_basa_tenant_nome
    t = db.scalar(select(Tenant).where(Tenant.name == nome, Tenant.is_active.is_(True)))
    if t is None:
        raise HTTPException(404, "tenant não configurado")
    return {"tenant_id": str(t.id), "nome": t.name}


@router.post("/login", response_model=TokenOut)
def login(
    body: LoginIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> TokenOut:
    chave = f"{body.tenant_id}:{body.email.lower()}"
    if _bloqueado(chave):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "muitas tentativas; aguarde 15 min")
    token = current_tenant_id.set(body.tenant_id)  # users está sob RLS: fixa o tenant do login
    try:
        user = db.scalar(
            select(User).where(
                User.email == body.email.lower(),
                User.tenant_id == body.tenant_id,
                User.is_active.is_(True),
            )
        )
    finally:
        current_tenant_id.reset(token)
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        _falhou(chave)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "credenciais inválidas")
    principal = Principal(
        user.id, user.tenant_id, user.role, user.oab, mfa_verified=False, email=user.email
    )
    return TokenOut(
        access_token=issue_token(principal, settings, ttl_seconds=300),
        mfa_required=True,
    )


@router.post("/mfa", response_model=TokenOut)
def mfa(
    body: MfaIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> TokenOut:
    principal = decode_token(body.token, settings)
    chave = f"mfa:{principal.user_id}"
    if _bloqueado(chave):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "muitas tentativas; aguarde 15 min")
    user = _usuario(db, principal.tenant_id, principal.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "usuário inválido")
    ok = False
    if user.mfa_enabled and (user.mfa_secret or "").startswith("f1:"):
        seg = totp.decifrar(user.mfa_secret or "", settings.secret_key)
        ok = bool(seg and totp.verificar(seg, body.code))
    elif settings.app_env in ("dev", "test") and not os.getenv("RAILWAY_ENVIRONMENT"):
        # código fixo só fora da nuvem (dev local e testes), qualquer que seja o APP_ENV lá
        ok = MFAPlaceholder.verify(body.code)
    if not ok:
        _falhou(chave)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "código MFA inválido")
    principal.mfa_verified = True
    token = current_tenant_id.set(principal.tenant_id)
    try:
        user.last_login_at = datetime.now(UTC)
        db.commit()
    finally:
        current_tenant_id.reset(token)
    return TokenOut(access_token=issue_token(principal, settings))


# --- convite ------------------------------------------------------------------------------


class ConviteSenhaIn(BaseModel):
    convite: str
    senha: str = Field(min_length=SENHA_MIN, max_length=200)


class ConviteConfirmarIn(BaseModel):
    convite: str
    codigo: str


def _do_convite(db: Session, convite: str, settings: Settings) -> User:
    p = decode_token(convite, settings, finalidade="convite")
    u = _usuario(db, p.tenant_id, p.user_id)
    if u is None or not u.is_active or u.mfa_enabled:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "convite inválido ou já usado")
    return u


@router.post("/convite/senha")
def convite_senha(
    body: ConviteSenhaIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    u = _do_convite(db, body.convite, settings)
    seg = totp.gerar_segredo()
    token = current_tenant_id.set(u.tenant_id)
    try:
        u.password_hash = hash_password(body.senha)
        u.mfa_secret = totp.cifrar(seg, settings.secret_key)
        u.mfa_enabled = False
        db.commit()
    finally:
        current_tenant_id.reset(token)
    return {"otpauth": totp.uri(seg, u.email), "segredo": seg}


@router.post("/convite/confirmar")
def convite_confirmar(
    body: ConviteConfirmarIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    u = _do_convite(db, body.convite, settings)
    seg = totp.decifrar(u.mfa_secret or "", settings.secret_key)
    if not seg or not totp.verificar(seg, body.codigo):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "código inválido; confira o relógio do celular"
        )
    token = current_tenant_id.set(u.tenant_id)
    try:
        u.mfa_enabled = True
        db.commit()
    finally:
        current_tenant_id.reset(token)
    return {"ativo": True}
