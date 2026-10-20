"""Águia Peregrina — aplicação FastAPI."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from fastapi import FastAPI, Header, HTTPException

from app import __version__
from app.api import api_router
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.observabilidade import iniciar_sentry
from app.core.tenancy import TenantMiddleware, install_tenant_guard
from app.schemas.common import Health

settings = get_settings()
logging.basicConfig(level=settings.log_level)
iniciar_sentry("web")

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


@app.post("/health/llm/ping", tags=["ops"])
def health_llm_ping(
    x_ops_key: str | None = Header(default=None, alias="X-Ops-Key"),
    model: str | None = None,
) -> dict[str, object]:
    """Chamada real mínima ao LLM para validar chave, roteamento e custo.

    Exige header X-Ops-Key igual a OPS_KEY (se OPS_KEY não estiver definido, 404).
    Não grava em llm_calls (sem tenant) e não envia dado pessoal.
    """
    import secrets as _secrets

    from app.llm.client import LLMClient

    if (
        not settings.ops_key
        or not x_ops_key
        or not _secrets.compare_digest(x_ops_key, settings.ops_key)
    ):
        raise HTTPException(status_code=404)
    client = LLMClient()
    started = time.perf_counter()
    resp = client.complete(
        [{"role": "user", "content": "Responda apenas com a palavra: pronto"}],
        purpose="ops.ping",
        model=model or settings.llm_small_model,
        max_tokens=16,
        temperature=0,
    )
    return {
        "effective": "fake" if client.fake else "live",
        "model": resp.model,
        "provider_model": resp.provider_model,
        "content": resp.content.strip()[:80],
        "input_tokens": resp.input_tokens,
        "output_tokens": resp.output_tokens,
        "cost_usd": resp.cost_usd,
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }
