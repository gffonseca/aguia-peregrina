"""Multi-tenancy: contexto do tenant, middleware e mixin de modelo.

Duas camadas de isolamento:
1. Postgres RLS (policies na migração inicial, GUC `app.tenant_id`).
2. Defesa em profundidade na aplicação: `TenantMixin` + `TenantScopedQuery`
   filtram por `tenant_id` do contexto e impedem escrita cruzada.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Any

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, Session, mapped_column, with_loader_criteria
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

current_tenant_id: ContextVar[uuid.UUID | None] = ContextVar("current_tenant_id", default=None)

TENANT_HEADER = "X-Tenant-ID"
TENANT_KINDS = ("law_firm", "credit_buyer")


class TenantMixin:
    """Toda tabela de negócio herda deste mixin (tenant_id obrigatório e indexado)."""

    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)


class TenantIsolationError(PermissionError):
    pass


def require_tenant() -> uuid.UUID:
    tenant_id = current_tenant_id.get()
    if tenant_id is None:
        raise TenantIsolationError("tenant_id ausente no contexto")
    return tenant_id


def install_tenant_guard(session_factory: Any) -> None:
    """Registra nos eventos da sessão o filtro automático e a checagem de escrita."""
    from sqlalchemy import event

    @event.listens_for(session_factory, "do_orm_execute")
    def _filter_by_tenant(state: Any) -> None:
        tenant_id = current_tenant_id.get()
        if tenant_id is None or not state.is_select:
            return
        state.statement = state.statement.options(
            with_loader_criteria(
                TenantMixin,
                lambda cls: cls.tenant_id == tenant_id,
                include_aliases=True,
            )
        )

    @event.listens_for(session_factory, "before_flush")
    def _guard_writes(session: Session, flush_context: Any, instances: Any) -> None:
        tenant_id = current_tenant_id.get()
        if tenant_id is None:
            return
        for obj in list(session.new) + list(session.dirty) + list(session.deleted):
            if isinstance(obj, TenantMixin):
                if getattr(obj, "tenant_id", None) is None:
                    obj.tenant_id = tenant_id
                elif obj.tenant_id != tenant_id:
                    raise TenantIsolationError(
                        f"escrita cruzada bloqueada: objeto do tenant {obj.tenant_id} "
                        f"no contexto {tenant_id}"
                    )


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve o tenant do request (header no MVP; depois do JWT) e o coloca no contexto."""

    exempt_paths = ("/health", "/docs", "/openapi.json", "/redoc", "/auth/login", "/auth/mfa")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self.exempt_paths or request.url.path.startswith(
            ("/docs", "/health/")
        ):
            return await call_next(request)
        raw = request.headers.get(TENANT_HEADER)
        if raw is None and getattr(request.state, "user", None) is not None:
            raw = str(request.state.user.get("tenant_id"))
        if not raw:
            return JSONResponse({"detail": f"header {TENANT_HEADER} obrigatório"}, status_code=400)
        try:
            tenant_id = uuid.UUID(raw)
        except ValueError:
            return JSONResponse({"detail": "tenant_id inválido"}, status_code=400)
        token = current_tenant_id.set(tenant_id)
        try:
            return await call_next(request)
        finally:
            current_tenant_id.reset(token)
