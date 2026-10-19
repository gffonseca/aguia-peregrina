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
