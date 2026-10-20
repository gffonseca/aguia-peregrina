"""Faturamento BASA e motor de oportunidades (M12).

- `basa_fichas`: carteira do Banco no Benner (export "Fichas.xlsx"), uma linha por ficha.
- `basa_atos_cobrados`: atos das prestações de contas mensais (uma competência substitui a
  anterior por inteiro na reimportação).
- `datajud_processos`: movimentos enxutos por processo (código, nome, data, complementos),
  últimos 24 meses, mesclados por grau; a fonte do motor.
- `motor_execucoes`: uma linha por rodada do motor, com estatísticas e o relatório .xlsx.
- `motor_oportunidades`: as oportunidades da última rodada (fila, perdidas, alertas).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JSONType, TenantModel


class BasaFicha(TenantModel):
    __tablename__ = "basa_fichas"
    __table_args__ = (UniqueConstraint("tenant_id", "ficha", name="uq_basa_fichas_ficha"),)

    ficha: Mapped[str] = mapped_column(String(30))
    cnj: Mapped[str] = mapped_column(String(25), index=True)  # só dígitos quando é CNJ
    situacao: Mapped[str] = mapped_column(String(40))
    categoria: Mapped[str | None] = mapped_column(String(20))  # civel | trabalhista
    adverso: Mapped[str | None] = mapped_column(String(200))
    valor_causa: Mapped[float | None] = mapped_column(Float)
    cadastrado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    importado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BasaAtoCobrado(TenantModel):
    __tablename__ = "basa_atos_cobrados"
    __table_args__ = (Index("ix_basa_atos_comp_cnj", "tenant_id", "competencia", "cnj"),)

    competencia: Mapped[str] = mapped_column(String(7))  # AAAA-MM
    cnj: Mapped[str] = mapped_column(String(25), index=True)
    ficha: Mapped[str | None] = mapped_column(String(30))
    uf: Mapped[str | None] = mapped_column(String(2))
    ato_id: Mapped[str | None] = mapped_column(String(60))
    ato_texto: Mapped[str] = mapped_column(Text)
    data: Mapped[date | None] = mapped_column(Date)
    valor: Mapped[float | None] = mapped_column(Float)


class DataJudProcesso(TenantModel):
    __tablename__ = "datajud_processos"
    __table_args__ = (UniqueConstraint("tenant_id", "cnj", name="uq_datajud_processos_cnj"),)

    cnj: Mapped[str] = mapped_column(String(20))
    tribunal: Mapped[str] = mapped_column(String(10))
    classe: Mapped[str | None] = mapped_column(String(200))
    # {"<_id do DataJud>": {"grau": "G1", "classe": "...", "atualizado": "...",
    #                       "movimentos": [[codigo, nome, "AAAA-MM-DD", ["compl", ...]], ...]}}
    graus: Mapped[dict] = mapped_column(JSONType, default=dict)
    ultima_movimentacao: Mapped[date | None] = mapped_column(Date)
    datajud_atualizado: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    buscado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MotorExecucao(TenantModel):
    __tablename__ = "motor_execucoes"

    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    terminado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), default="rodando"
    )  # rodando|ok|erro|interrompida|pedido|executando|atendido
    referencia: Mapped[date] = mapped_column(Date)  # "hoje" da rodada
    estatisticas: Mapped[dict] = mapped_column(JSONType, default=dict)
    relatorio_xlsx: Mapped[bytes | None] = mapped_column(LargeBinary)
    erro: Mapped[str | None] = mapped_column(Text)


class MotorOportunidade(TenantModel):
    __tablename__ = "motor_oportunidades"
    __table_args__ = (Index("ix_motor_op_exec_status", "tenant_id", "execucao_id", "status"),)

    execucao_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("motor_execucoes.id", ondelete="CASCADE")
    )
    cnj: Mapped[str] = mapped_column(String(20), index=True)
    ficha: Mapped[str | None] = mapped_column(String(30))
    evento: Mapped[str] = mapped_column(String(80))
    data_evento: Mapped[date] = mapped_column(Date)
    ato_id: Mapped[str | None] = mapped_column(String(60))
    valor: Mapped[float | None] = mapped_column(Float)
    papel: Mapped[str | None] = mapped_column(String(10))
    prazo: Mapped[date | None] = mapped_column(Date)
    confianca: Mapped[str] = mapped_column(String(10))
    movimento: Mapped[str | None] = mapped_column(Text)
    observacao: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10))  # ABERTA|ATENDIDA|PERDIDA|ALERTA
    atendida_por: Mapped[str | None] = mapped_column(String(80))


class BasaRecebivel(TenantModel):
    """Uma prestação por competência e UF (o BASA paga PA e AM em NFs separadas)."""

    __tablename__ = "basa_recebiveis"
    __table_args__ = (
        UniqueConstraint("tenant_id", "competencia", "uf", name="uq_basa_recebiveis_comp_uf"),
    )

    competencia: Mapped[str] = mapped_column(String(7))
    uf: Mapped[str] = mapped_column(String(2))
    valor_declarado: Mapped[float | None] = mapped_column(Float)
    valor_faturavel: Mapped[float | None] = mapped_column(Float)
    atos: Mapped[int | None] = mapped_column()
    enviado_em: Mapped[date | None] = mapped_column(Date)
    conferido_em: Mapped[date | None] = mapped_column(Date)
    valor_aprovado: Mapped[float | None] = mapped_column(Float)
    nf_numero: Mapped[str | None] = mapped_column(String(40))
    nf_emitida_em: Mapped[date | None] = mapped_column(Date)
    nf_valor: Mapped[float | None] = mapped_column(Float)
    pago_em: Mapped[date | None] = mapped_column(Date)
    valor_pago: Mapped[float | None] = mapped_column(Float)
    observacao: Mapped[str | None] = mapped_column(Text)
    # trilha: [{"em": iso, "por": "...", "campo": "...", "de": ..., "para": ...}]
    historico: Mapped[list] = mapped_column(JSONType, default=list)


class OportunidadeDecisao(TenantModel):
    """O que a equipe decidiu sobre uma oportunidade do motor; sobrevive às rodadas diárias
    (a chave é processo + evento + data do evento, não o id da rodada)."""

    __tablename__ = "motor_decisoes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "cnj", "evento", "data_evento", name="uq_motor_decisao"),
    )

    cnj: Mapped[str] = mapped_column(String(20), index=True)
    evento: Mapped[str] = mapped_column(String(80))
    data_evento: Mapped[date] = mapped_column(Date)
    decisao: Mapped[str] = mapped_column(String(12))  # feito | nao_cabe | em_andamento
    observacao: Mapped[str | None] = mapped_column(Text)
    por: Mapped[str] = mapped_column(String(80))
    em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
