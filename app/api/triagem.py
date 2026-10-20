"""Triagem da caixa basa@ (M13). Protegido por X-Ops-Key + X-Tenant-ID.

- `GET  /triagem?pessoa=email&status=pendente&dias=30`: resumo por papel (o painel usa).
- `PATCH /triagem/{id}` `{"status": "visto"|"resolvido"|"pendente"}` (X-Usuario na trilha).
- `GET  /triagem/papeis` · `PUT /triagem/papeis/{papel}` `[{"nome","email"}]`.
- `POST /triagem/importar?caixa=`: mensagens no formato do Graph (lista JSON) — para carga
  inicial ou teste sem o app do Entra. `POST /triagem/sincronizar`: lê a caixa agora.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import DB, require_ops_key, tenant_id_dep
from app.core.config import get_settings
from app.integrations.msgraph.client import GraphMailClient, para_email
from app.modules.m13_triagem import servico

router = APIRouter(prefix="/triagem", tags=["triagem"], dependencies=[Depends(require_ops_key)])


@router.get("")
def resumo(
    pessoa: str | None = None,
    status: str | None = Query(default="pendente", pattern="^(pendente|visto|resolvido)$"),
    dias: int = Query(default=30, ge=1, le=365),
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> dict[str, Any]:
    servico.garantir_papeis(db, tenant_id)
    return servico.resumo(db, pessoa=pessoa, status=status, dias=dias)


@router.patch("/{tid}")
def marcar(
    tid: uuid.UUID,
    corpo: dict[str, Any] = Body(...),
    x_usuario: str = Header(default="painel", alias="X-Usuario"),
    db: Session = DB,
) -> dict[str, Any]:
    try:
        return servico.marcar(db, tid, str(corpo.get("status")), x_usuario)
    except KeyError:
        raise HTTPException(404, "e-mail não encontrado") from None
    except ValueError as e:
        raise HTTPException(422, str(e)) from None


@router.get("/papeis")
def papeis(db: Session = DB, tenant_id: uuid.UUID = Depends(tenant_id_dep)) -> list[dict[str, Any]]:
    servico.garantir_papeis(db, tenant_id)
    return servico.papeis(db)


@router.put("/papeis/{papel}")
def definir_papel(
    papel: str,
    pessoas: list[dict[str, str]] = Body(...),
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> dict[str, Any]:
    return servico.definir_papel(db, tenant_id, papel, pessoas)


@router.post("/importar")
def importar(
    mensagens: list[dict[str, Any]] = Body(...),
    caixa: str = Query(default="importacao"),
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> dict[str, int]:
    return servico.ingerir(db, tenant_id, [para_email(m) for m in mensagens], caixa)


@router.post("/sincronizar")
def sincronizar(db: Session = DB, tenant_id: uuid.UUID = Depends(tenant_id_dep)) -> dict[str, int]:
    s = get_settings()
    if not (
        s.triagem_caixa and s.msgraph_tenant_id and s.msgraph_client_id and s.msgraph_client_secret
    ):
        raise HTTPException(409, "caixa ou app do Microsoft 365 não configurados")
    cli = GraphMailClient(s.msgraph_tenant_id, s.msgraph_client_id, s.msgraph_client_secret)
    return servico.sincronizar_caixa(db, tenant_id, cli, s.triagem_caixa)
