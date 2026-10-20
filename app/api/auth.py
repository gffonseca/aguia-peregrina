"""Auth stub: login por e-mail/senha + MFA placeholder. Substituir antes de dados reais."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.security import MFAPlaceholder, Principal, decode_token, issue_token, verify_password
from app.core.tenancy import current_tenant_id
from app.models.tenant import User
from app.schemas.auth import LoginIn, MfaIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(
    body: LoginIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> TokenOut:
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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "credenciais inválidas")
    principal = Principal(user.id, user.tenant_id, user.role, user.oab, mfa_verified=False)
    return TokenOut(
        access_token=issue_token(principal, settings, ttl_seconds=300),
        mfa_required=True,
    )


@router.post("/mfa", response_model=TokenOut)
def mfa(body: MfaIn, settings: Settings = Depends(get_settings)) -> TokenOut:
    principal = decode_token(body.token, settings)
    if not MFAPlaceholder.verify(body.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "código MFA inválido")
    principal.mfa_verified = True
    return TokenOut(access_token=issue_token(principal, settings))
