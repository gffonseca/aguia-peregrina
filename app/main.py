"""Águia Peregrina — aplicação FastAPI."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import FastAPI

from app import __version__
from app.api import api_router
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.tenancy import TenantMiddleware, install_tenant_guard
from app.schemas.common import Health

settings = get_settings()
logging.basicConfig(level=settings.log_level)

install_tenant_guard(SessionLocal)

app = FastAPI(
    title="Águia Peregrina",
    version=__version__,
    description=(
        "Esteira de IA para contencioso de massa (defesa) e compra de créditos judiciais — "
        "plataforma unificada multi-tenant. Toda peça tem advogado identificado; nada é "
        "exportado sem aprovação; nenhum rótulo de fraude sem decisão humana."
    ),
)
app.add_middleware(TenantMiddleware)
app.include_router(api_router)


@app.get("/health", response_model=Health, tags=["ops"])
def health() -> Health:
    return Health(status="ok", version=__version__, env=settings.app_env, time=datetime.now(UTC))


@app.get("/health/llm", tags=["ops"])
def health_llm() -> dict[str, object]:
    """Diagnóstico do gateway de LLM: modo efetivo e quais chaves estão configuradas.

    Nunca expõe valores — só presença (bool) e o modo resolvido (fake/live).
    """
    from app.llm.client import LITELLM_AVAILABLE, LLMClient

    client = LLMClient()
    return {
        "llm_mode_config": settings.llm_mode,
        "effective": "fake" if client.fake else "live",
        "litellm_available": LITELLM_AVAILABLE,
        "keys_present": {
            "anthropic": bool(settings.anthropic_api_key),
            "openai": bool(settings.openai_api_key),
        },
        "default_model": settings.llm_default_model,
        "small_model": settings.llm_small_model,
    }
