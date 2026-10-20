"""Correções no Benner (M14): a fila única que a equipe aplica à mão (opção assistida) e que o
robô aplica depois (Fase 3), sempre com o mesmo registro de quem fez o quê.

Autorização do BASA para automação no Benner: arquivada no administrativo do FBS
(informado por Gustavo Fonseca em 20/10/2026; documento confidencial, não anexado aqui).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JSONType, TenantModel


class BennerCorrecao(TenantModel):
    __tablename__ = "benner_correcoes"
    __table_args__ = (UniqueConstraint("tenant_id", "chave", name="uq_benner_correcao_chave"),)

    # SITUACAO | NUMERO_PROCESSO | FICHA_INEXISTENTE | SUBIR_PECA
    tipo: Mapped[str] = mapped_column(String(30), index=True)
    chave: Mapped[str] = mapped_column(String(300))  # tipo|ficha|referência — evita duplicar
    ficha: Mapped[str | None] = mapped_column(String(30), index=True)
    cnj: Mapped[str | None] = mapped_column(String(25))
    campo: Mapped[str | None] = mapped_column(String(60))
    valor_atual: Mapped[str | None] = mapped_column(String(300))
    valor_proposto: Mapped[str | None] = mapped_column(String(300))
    confianca: Mapped[str] = mapped_column(String(10), default="alta")  # alta | media
    evidencia: Mapped[str | None] = mapped_column(Text)
    origem: Mapped[str | None] = mapped_column(String(60))  # datajud, prestacao, conferencia
    # pendente → feito (equipe/robô) → confirmado (visto no export seguinte) | nao_procede
    status: Mapped[str] = mapped_column(String(14), default="pendente", index=True)
    aplicado_por: Mapped[str | None] = mapped_column(String(80))  # pessoa ou "robô"
    aplicado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observacao: Mapped[str | None] = mapped_column(Text)
    historico: Mapped[list] = mapped_column(JSONType, default=list)
