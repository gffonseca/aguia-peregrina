"""Triagem da caixa basa@ (M13): um registro por e-mail e a tabela papel → pessoas.

Guarda só o necessário para o resumo (remetente, assunto, trecho de até 600 caracteres, link
para abrir no Outlook); o e-mail inteiro continua só na caixa.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JSONType, TenantModel


class TriagemEmail(TenantModel):
    __tablename__ = "triagem_emails"
    __table_args__ = (UniqueConstraint("tenant_id", "mensagem_id", name="uq_triagem_msg"),)

    mensagem_id: Mapped[str] = mapped_column(String(400))
    caixa: Mapped[str] = mapped_column(String(200))
    recebido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    remetente: Mapped[str] = mapped_column(String(200))
    assunto: Mapped[str] = mapped_column(String(500))
    trecho: Mapped[str | None] = mapped_column(Text)
    # intimações do DJEN: o texto inteiro da decisão (base para a IA redigir a peça)
    texto_integral: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(Text)
    conversa: Mapped[str | None] = mapped_column(String(400))
    categoria: Mapped[str] = mapped_column(String(30), index=True)
    urgencia: Mapped[str] = mapped_column(String(10))
    papeis: Mapped[list] = mapped_column(JSONType, default=list)
    cnjs: Mapped[list] = mapped_column(JSONType, default=list)
    fichas: Mapped[list] = mapped_column(JSONType, default=list)
    uf: Mapped[str | None] = mapped_column(String(2))
    motivo: Mapped[str | None] = mapped_column(String(200))
    acao: Mapped[str | None] = mapped_column(Text)
    internos_copiados: Mapped[int] = mapped_column(Integer, default=0)
    internos_necessarios: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(12), default="pendente")  # pendente|visto|resolvido
    tratado_por: Mapped[str | None] = mapped_column(String(80))
    tratado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TriagemPapel(TenantModel):
    __tablename__ = "triagem_papeis"
    __table_args__ = (UniqueConstraint("tenant_id", "papel", name="uq_triagem_papel"),)

    papel: Mapped[str] = mapped_column(String(40))
    descricao: Mapped[str | None] = mapped_column(String(200))
    # [{"nome": "...", "email": "..."}]
    pessoas: Mapped[list] = mapped_column(JSONType, default=list)
