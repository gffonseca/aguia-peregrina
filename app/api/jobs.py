"""Consulta de jobs assíncronos do engine in_process (`dispatch_async`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import principal_in_tenant
from app.core.security import Principal
from app.workflows.engine import get_engine

router = APIRouter(prefix="/jobs", tags=["jobs"])


def dispatch(job_name: str, payload: dict, *, wait: bool) -> dict:
    """Dispara um job; síncrono (`wait=true`) ou em background com referência para polling."""
    engine = get_engine()
    if not wait and hasattr(engine, "dispatch_async"):
        ref = engine.dispatch_async(job_name, payload)
        return {"job": ref, "engine": engine.name, "async": True, "status": "running"}
    ref = engine.dispatch(job_name, payload)
    out: dict = {"job": ref, "engine": engine.name, "async": False}
    result_for = getattr(engine, "result_for", None)
    if result_for is not None:  # in_process: devolve o resultado da execução
        out["result"] = result_for(ref)
    return out


@router.get("/{ref}")
def job_status(ref: str, _: Principal = Depends(principal_in_tenant)) -> dict:
    engine = get_engine()
    status = getattr(engine, "job_status", None)
    if status is None:
        raise HTTPException(501, "engine sem consulta de jobs (use o painel do Hatchet)")
    entry = status(ref)
    if entry is None:
        raise HTTPException(404, "job desconhecido (ou expirado)")
    return {"job": ref, **entry}
