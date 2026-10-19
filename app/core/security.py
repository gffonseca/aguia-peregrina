"""Autenticação mínima: tokens assinados (HMAC) e placeholder de MFA.

No MVP a autenticação é um stub. Antes de dados reais: trocar por JWT com rotação,
MFA TOTP obrigatório para advogados revisores e sessão curta.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


@dataclass
class Principal:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str
    oab: str | None
    mfa_verified: bool


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or uuid.uuid4().hex
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"pbkdf2$200000${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, _, salt, digest = stored.split("$")
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt).split("$")[-1], digest)


def _sign(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def issue_token(principal: Principal, settings: Settings, ttl_seconds: int = 8 * 3600) -> str:
    body = {
        "sub": str(principal.user_id),
        "tenant_id": str(principal.tenant_id),
        "role": principal.role,
        "oab": principal.oab,
        "mfa": principal.mfa_verified,
        "exp": int(time.time()) + ttl_seconds,
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    b64 = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return f"{b64}.{_sign(raw, settings.secret_key)}"


def decode_token(token: str, settings: Settings) -> Principal:
    try:
        b64, sig = token.split(".")
        raw = base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token malformado") from exc
    if not hmac.compare_digest(_sign(raw, settings.secret_key), sig):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "assinatura inválida")
    body: dict[str, Any] = json.loads(raw)
    if body.get("exp", 0) < time.time():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expirado")
    return Principal(
        user_id=uuid.UUID(body["sub"]),
        tenant_id=uuid.UUID(body["tenant_id"]),
        role=body["role"],
        oab=body.get("oab"),
        mfa_verified=bool(body.get("mfa")),
    )


def get_current_principal(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authorization: Bearer <token> ausente")
    return decode_token(authorization.split(" ", 1)[1], settings)


def require_mfa(principal: Principal = Depends(get_current_principal)) -> Principal:
    """Ações sensíveis (aprovar peça, exportar, rotular fraude) exigem MFA verificado."""
    if not principal.mfa_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "MFA obrigatório para esta ação")
    return principal


def require_lawyer(principal: Principal = Depends(require_mfa)) -> Principal:
    """Aprovação de peça exige advogado inscrito (OAB) identificado."""
    if principal.role not in {"lawyer", "partner"} or not principal.oab:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "ação reservada a advogado com OAB")
    return principal


class MFAPlaceholder:
    """Placeholder de MFA TOTP. Substituir por pyotp + segredo cifrado por usuário."""

    @staticmethod
    def verify(code: str) -> bool:
        return code == "000000"  # DEV ONLY
