"""Endpoints operacionais de integrações (protegidos por `X-Ops-Key`, como /health/llm/ping).

- `GET  /integrations/legalone/probe`: quais recursos da API respondem (sem gravar nada;
  não exige tenant).
- `POST /integrations/legalone/sync`: dispara o sync incremental para o tenant do header
  `X-Tenant-ID`. Síncrono com `WORKFLOW_ENGINE=in_process`; enfileirado no Hatchet caso
  contrário.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import require_ops_key, tenant_id_dep
from app.integrations.legalone.client import LegalOneError, get_legalone_client
from app.integrations.legalone.sync import DEFAULT_RESOURCES
from app.workflows.engine import get_engine

router = APIRouter(
    prefix="/integrations/legalone",
    tags=["integrations (Legal One)"],
    dependencies=[Depends(require_ops_key)],
)


class LegalOneSyncIn(BaseModel):
    since: str | None = Field(
        default="auto", description="YYYY-MM-DD, 'auto' (última execução ok) ou null = tudo"
    )
    max_pages: int | None = Field(default=50, ge=1, le=5000)
    resources: list[str] = Field(default_factory=lambda: list(DEFAULT_RESOURCES))


@router.get("/probe")
def probe() -> dict:
    client = get_legalone_client()
    if not client.configured:
        raise HTTPException(503, "LEGALONE_CLIENT_ID/LEGALONE_CLIENT_SECRET não configurados")
    try:
        return client.probe()
    except LegalOneError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/sync", status_code=202)
def sync(body: LegalOneSyncIn, tenant_id: uuid.UUID = Depends(tenant_id_dep)) -> dict:
    unknown = sorted(set(body.resources) - set(DEFAULT_RESOURCES))
    if unknown:
        raise HTTPException(422, f"recursos desconhecidos: {unknown}")
    client = get_legalone_client()
    if not client.configured:
        raise HTTPException(503, "LEGALONE_CLIENT_ID/LEGALONE_CLIENT_SECRET não configurados")
    payload = {
        "tenant_id": str(tenant_id),
        "since": body.since,
        "max_pages": body.max_pages,
        "resources": body.resources,
    }
    engine = get_engine()
    try:
        ref = engine.dispatch("sync_legalone", payload)
    except LegalOneError as exc:
        raise HTTPException(502, str(exc)) from exc
    result: dict = {"job": "sync_legalone", "engine": engine.name, "ref": ref}
    history = getattr(engine, "history", None)
    if history:  # in_process: devolve as estatísticas da execução
        result["result"] = history[-1][2]
    return result
