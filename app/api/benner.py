"""Fila de correções no Benner (M14). X-Ops-Key + X-Tenant-ID.

- `POST /benner/correcoes/gerar`: recalcula a fila (DataJud, fichas, prestações).
- `GET  /benner/correcoes?status=pendente&tipo=`: itens e resumo.
- `GET  /benner/correcoes.xlsx?status=pendente`: lote para a CCONS.
- `PATCH /benner/correcoes/{id}` `{"status": "feito"|"nao_procede"|"pendente", "observacao"}`.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import DB, Operador, require_operador, tenant_id_dep
from app.modules.m14_benner import correcoes

router = APIRouter(prefix="/benner", tags=["benner"], dependencies=[Depends(require_operador)])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/documentos")
async def documentos(
    arquivos: list[UploadFile] = File(...),
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> dict[str, int]:
    """Exports 'Pesquisa de documentos' do Benner → base do conferente e da prestação."""
    from app.modules.m12_faturamento.conferencia import ler_documentos
    from app.modules.m12_faturamento.prestacao_auto import guardar_documentos

    docs = ler_documentos([await a.read() for a in arquivos])
    return {"lidos": len(docs), **guardar_documentos(db, tenant_id, docs)}


@router.post("/conciliacao/legalone", response_model=None)
async def conciliacao_legalone(
    arquivo: UploadFile = File(...),
    formato: str = Query(default="xlsx", pattern="^(xlsx|json)$"),
    db: Session = DB,
) -> Response | dict[str, Any]:
    """Export do Legal One × carteira do Benner → o que cadastrar, conferir e encerrar."""
    from app.modules.m14_benner.conciliacao import conciliar, ler_legalone

    dados, rs = conciliar(db, ler_legalone(await arquivo.read(), arquivo.filename or ""))
    if formato == "json":
        return rs
    return Response(
        dados,
        media_type=XLSX,
        headers={"Content-Disposition": 'attachment; filename="conciliacao-benner-legalone.xlsx"'},
    )


@router.post("/correcoes/gerar")
def gerar(db: Session = DB, tenant_id: uuid.UUID = Depends(tenant_id_dep)) -> dict[str, int]:
    return correcoes.gerar(db, tenant_id)


@router.get("/correcoes")
def listar(
    status: str | None = Query(
        default="pendente", pattern="^(pendente|feito|confirmado|nao_procede|superado)$"
    ),
    tipo: str | None = Query(
        default=None, pattern="^(SITUACAO|NUMERO_PROCESSO|FICHA_INEXISTENTE|SUBIR_PECA)$"
    ),
    limite: int = Query(default=200, ge=1, le=5000),
    db: Session = DB,
) -> dict[str, Any]:
    return correcoes.listar(db, status=status, tipo=tipo, limite=limite)


@router.get("/correcoes.xlsx")
def planilha(status: str = "pendente", db: Session = DB) -> Response:
    return Response(
        correcoes.planilha(db, status=status),
        media_type=XLSX,
        headers={"Content-Disposition": 'attachment; filename="correcoes-benner.xlsx"'},
    )


@router.patch("/correcoes/{cid}")
def marcar(
    cid: uuid.UUID,
    corpo: dict[str, Any] = Body(...),
    op: Operador = Depends(require_operador),
    db: Session = DB,
) -> dict[str, Any]:
    try:
        return correcoes.marcar(
            db, cid, str(corpo.get("status")), op.email, corpo.get("observacao")
        )
    except KeyError:
        raise HTTPException(404, "item não encontrado") from None
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
