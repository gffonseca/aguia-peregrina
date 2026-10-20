"""TOTP (RFC 6238) com a biblioteca padrão — compatível com Google/Microsoft Authenticator.

O segredo fica cifrado no banco (Fernet com chave derivada de SECRET_KEY): quem lê o banco não
gera códigos sem a variável de ambiente.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken

PASSO = 30
DIGITOS = 6


def gerar_segredo() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def codigo(segredo: str, instante: float | None = None) -> str:
    chave = base64.b32decode(segredo + "=" * (-len(segredo) % 8), casefold=True)
    contador = int((time.time() if instante is None else instante) // PASSO)
    h = hmac.new(chave, struct.pack(">Q", contador), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    n = (struct.unpack(">I", h[o : o + 4])[0] & 0x7FFFFFFF) % 10**DIGITOS
    return str(n).zfill(DIGITOS)


def verificar(segredo: str, informado: str, janela: int = 1, instante: float | None = None) -> bool:
    """Aceita o código do passo atual e de ±`janela` passos (relógio do celular fora)."""
    informado = "".join(c for c in informado if c.isdigit())
    if len(informado) != DIGITOS:
        return False
    t = time.time() if instante is None else instante
    return any(
        hmac.compare_digest(codigo(segredo, t + d * PASSO), informado)
        for d in range(-janela, janela + 1)
    )


def uri(segredo: str, conta: str, emissor: str = "Aguia Peregrina FBS") -> str:
    return (
        f"otpauth://totp/{quote(emissor)}:{quote(conta)}?secret={segredo}"
        f"&issuer={quote(emissor)}&digits={DIGITOS}&period={PASSO}"
    )


def _fernet(chave_app: str) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(("totp:" + chave_app).encode()).digest()))


def cifrar(segredo: str, chave_app: str) -> str:
    return "f1:" + _fernet(chave_app).encrypt(segredo.encode()).decode()


def decifrar(guardado: str, chave_app: str) -> str | None:
    if not guardado.startswith("f1:"):
        return None
    try:
        return _fernet(chave_app).decrypt(guardado[3:].encode()).decode()
    except InvalidToken:
        return None
