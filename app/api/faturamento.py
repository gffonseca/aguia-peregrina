"""M12 — faturamento BASA e motor de oportunidades (protegido por `X-Ops-Key` + `X-Tenant-ID`).

- `POST /faturamento/basa/setup` (sem tenant): garante o tenant do escritório e devolve o id.
- `POST /faturamento/basa/fichas`: exports "Fichas.xlsx" do Benner (cível e trabalhista).
- `POST /faturamento/basa/prestacoes?competencia=AAAA-MM`: planilha de atos do mês; substitui
  a competência e devolve a pré-auditoria.
- `GET  /faturamento/basa/prestacoes/{competencia}/pre-auditoria.xlsx`: Anexo II por estado.
- `POST /faturamento/basa/conferencia?competencia=AAAA-MM[&formato=json]`: prestação + exports
  "Pesquisa de documentos" do Benner → pré-auditoria com a conferência (não grava nada).
- `GET  /faturamento/basa/recebiveis`: prestações por competência × UF, etapa, vencimento
  (cl. 18ª), alertas e minuta de cobrança (rascunho; nada é enviado).
- `PATCH /faturamento/basa/recebiveis/{id}`: lançamento manual (datas, NF, valores), com trilha.
- `POST /faturamento/basa/motor/rodar?completo=false`: roda o motor agora (assíncrono).
- `GET  /faturamento/basa/motor/ultima`: estatísticas da última rodada.
- `GET  /faturamento/basa/motor/ultima.xlsx`: relatório da última rodada.
- `GET  /faturamento/basa/oportunidades?status=ABERTA&confianca=alta&limite=200`.
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, require_ops_key, tenant_id_dep
from app.core.config import get_settings
from app.models.faturamento import BasaAtoCobrado, BasaFicha, MotorExecucao, MotorOportunidade
from app.models.tenant import Tenant
from app.modules.m12_faturamento.auditoria import FichaBenner, LinhaAto, auditar
from app.modules.m12_faturamento.planilhas import gerar_excel
from app.modules.m12_faturamento.servico import (
    atualizar_recebivel,
    cnj_formatado,
    conferir_prestacao,
    importar_fichas,
    importar_prestacao,
    listar_recebiveis,
)

router = APIRouter(
    prefix="/faturamento/basa", tags=["faturamento"], dependencies=[Depends(require_ops_key)]
)
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class SetupOut(BaseModel):
    tenant_id: uuid.UUID
    criado: bool


@router.post("/setup", response_model=SetupOut)
def setup(db: Session = DB) -> SetupOut:
    nome = get_settings().motor_basa_tenant_nome
    t = db.scalar(select(Tenant).where(Tenant.name == nome, Tenant.kind == "law_firm"))
    criado = t is None
    if t is None:
        t = Tenant(name=nome, kind="law_firm", settings={})
        db.add(t)
        db.commit()
    return SetupOut(tenant_id=t.id, criado=criado)


@router.post("/fichas")
async def fichas(
    arquivos: list[UploadFile] = File(...),
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> dict[str, int]:
    return importar_fichas(db, tenant_id, [await a.read() for a in arquivos])


@router.post("/prestacoes")
async def prestacoes(
    competencia: str = Query(pattern=r"^\d{4}-\d{2}$"),
    arquivo: UploadFile = File(...),
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> dict[str, Any]:
    return importar_prestacao(db, tenant_id, competencia, await arquivo.read())


@router.get("/prestacoes/{competencia}/pre-auditoria.xlsx")
def pre_auditoria(competencia: str, db: Session = DB) -> Response:
    atos = list(db.scalars(select(BasaAtoCobrado).where(BasaAtoCobrado.competencia == competencia)))
    if not atos:
        raise HTTPException(404, "competência não importada")
    fichas = {
        f.ficha: FichaBenner(f.ficha, f.cnj, f.situacao) for f in db.scalars(select(BasaFicha))
    }
    linhas = [
        LinhaAto(
            ficha=a.ficha or "",
            cnj=cnj_formatado(a.cnj),
            comarca="",
            uf=a.uf or "",
            acao="",
            parte_adversa="",
            ato_texto=a.ato_texto,
            data=a.data,
            valor=a.valor,
            origem=i + 2,
        )
        for i, a in enumerate(atos)
    ]
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "pre.xlsx"
        gerar_excel(auditar(linhas, competencia, fichas or None), competencia, out)
        data = out.read_bytes()
    return Response(
        data,
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="pre-auditoria-{competencia}.xlsx"'},
    )


@router.post("/conferencia", response_model=None)
async def conferencia(
    competencia: str = Query(pattern=r"^\d{4}-\d{2}$"),
    formato: str = Query(default="xlsx", pattern="^(xlsx|json)$"),
    prestacao: UploadFile = File(...),
    documentos: list[UploadFile] = File(...),
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> Response | dict[str, Any]:
    """Cada ato cobrado tem a peça no Benner? E que peças do mês ficaram sem cobrança?"""
    data, rs = conferir_prestacao(
        db, competencia, await prestacao.read(), [await d.read() for d in documentos]
    )
    if formato == "json":
        return rs
    return Response(
        data,
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="conferencia-{competencia}.xlsx"'},
    )


@router.get("/recebiveis")
def recebiveis(db: Session = DB) -> dict[str, Any]:
    return listar_recebiveis(db)


@router.patch("/recebiveis/{rid}")
def recebiveis_atualizar(
    rid: uuid.UUID,
    campos: dict[str, Any] = Body(...),
    x_usuario: str = Header(default="painel", alias="X-Usuario"),
    db: Session = DB,
) -> dict[str, Any]:
    try:
        return atualizar_recebivel(db, rid, campos, x_usuario)
    except KeyError:
        raise HTTPException(404, "recebível não encontrado") from None
    except ValueError as e:
        raise HTTPException(422, str(e)) from None


@router.post("/motor/rodar")
def motor_rodar(
    completo: bool = False,
    db: Session = DB,
    tenant_id: uuid.UUID = Depends(tenant_id_dep),
) -> dict[str, Any]:
    """Pede uma rodada ao worker (ele verifica pedidos a cada minuto). `completo=true` refaz a
    busca inteira no DataJud em vez da incremental."""
    pedido = MotorExecucao(
        tenant_id=tenant_id,
        iniciado_em=datetime.now(UTC),
        referencia=date.today(),
        status="pedido",
        estatisticas={"completo": completo},
    )
    db.add(pedido)
    db.commit()
    return {"pedido_id": str(pedido.id), "acompanhar": "/faturamento/basa/motor/ultima"}


def _ultima(db: Session) -> MotorExecucao:
    ex = db.scalar(
        select(MotorExecucao)
        .where(MotorExecucao.status == "ok")
        .order_by(MotorExecucao.iniciado_em.desc())
    )
    if ex is None:
        raise HTTPException(404, "nenhuma rodada concluída")
    return ex


@router.get("/motor/ultima")
def motor_ultima(db: Session = DB) -> dict[str, Any]:
    ex = _ultima(db)
    ultima_qualquer = db.scalar(select(MotorExecucao).order_by(MotorExecucao.iniciado_em.desc()))
    return {
        "execucao_id": str(ex.id),
        "referencia": ex.referencia.isoformat(),
        "iniciado_em": ex.iniciado_em.isoformat(),
        "terminado_em": ex.terminado_em.isoformat() if ex.terminado_em else None,
        "estatisticas": ex.estatisticas,
        "ultima_tentativa": {
            "status": ultima_qualquer.status,
            "erro": ultima_qualquer.erro,
            "iniciado_em": ultima_qualquer.iniciado_em.isoformat(),
        }
        if ultima_qualquer
        else None,
    }


@router.get("/motor/ultima.xlsx")
def motor_ultima_xlsx(db: Session = DB) -> Response:
    ex = _ultima(db)
    return Response(
        ex.relatorio_xlsx or b"",
        media_type=XLSX,
        headers={
            "Content-Disposition": (
                f'attachment; filename="motor-oportunidades-{ex.referencia.isoformat()}.xlsx"'
            )
        },
    )


@router.get("/oportunidades")
def oportunidades(
    status: str | None = Query(default=None, pattern="^(ABERTA|ATENDIDA|PERDIDA|ALERTA)$"),
    confianca: str | None = Query(default=None, pattern="^(alta|media)$"),
    evento: str | None = None,
    limite: int = Query(default=200, le=5000),
    db: Session = DB,
) -> list[dict[str, Any]]:
    q = select(MotorOportunidade)
    if status:
        q = q.where(MotorOportunidade.status == status)
    if confianca:
        q = q.where(MotorOportunidade.confianca == confianca)
    if evento:
        q = q.where(MotorOportunidade.evento == evento)
    q = q.order_by(MotorOportunidade.valor.desc().nullslast(), MotorOportunidade.data_evento)
    return [
        {
            "processo": cnj_formatado(o.cnj),
            "ficha": o.ficha,
            "evento": o.evento,
            "data_evento": o.data_evento.isoformat(),
            "ato": o.ato_id,
            "valor": o.valor,
            "papel": o.papel,
            "prazo": o.prazo.isoformat() if o.prazo else None,
            "confianca": o.confianca,
            "status": o.status,
            "observacao": o.observacao,
            "movimento": o.movimento,
            "atendida_por": o.atendida_por,
        }
        for o in db.scalars(q.limit(limite))
    ]
