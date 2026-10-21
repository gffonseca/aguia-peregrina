"""Correções no Benner (M14): a fila única que a equipe aplica à mão (opção assistida) e que o
robô aplica depois (Fase 3), sempre com o mesmo registro de quem fez o quê.

Autorização do BASA para automação no Benner: arquivada no administrativo do FBS
(informado por Gustavo Fonseca em 20/10/2026; documento confidencial, não anexado aqui).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, LargeBinary, String, Text, UniqueConstraint
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
    # pendente → aprovado (advogado liberou p/ o robô, com os parâmetros) → feito (equipe/robô)
    # → confirmado (visto no export seguinte) | nao_procede | superado
    status: Mapped[str] = mapped_column(String(14), default="pendente", index=True)
    aplicado_por: Mapped[str | None] = mapped_column(String(80))  # pessoa ou "robô"
    aplicado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observacao: Mapped[str | None] = mapped_column(Text)
    historico: Mapped[list] = mapped_column(JSONType, default=list)
    # o que o advogado decidiu ao liberar para o robô: SITUACAO → data/motivo/êxito do
    # encerramento; SUBIR_PECA → nome, tipo e data do documento (o arquivo vai em `anexo`)
    parametros: Mapped[dict | None] = mapped_column(JSONType)
    anexo_nome: Mapped[str | None] = mapped_column(String(255))
    anexo: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)


class BennerDocumento(TenantModel):
    """Documentos da 'Pesquisa de documentos' do Benner (export manual hoje; robô na Fase 3).
    Base do conferente e da prestação montada automaticamente."""

    __tablename__ = "benner_documentos"
    __table_args__ = (UniqueConstraint("tenant_id", "chave", name="uq_benner_doc_chave"),)

    chave: Mapped[str] = mapped_column(String(64))  # sha1 de cnj|ficha|data|nome|arquivo|autor
    data: Mapped[date | None] = mapped_column(Date, index=True)
    nome: Mapped[str] = mapped_column(String(500))
    tipo: Mapped[str | None] = mapped_column(String(200))
    ficha: Mapped[str | None] = mapped_column(String(30), index=True)
    cnj: Mapped[str | None] = mapped_column(String(25), index=True)
    incluido_por: Mapped[str | None] = mapped_column(String(200))
    arquivo: Mapped[str | None] = mapped_column(String(500))
    importado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
