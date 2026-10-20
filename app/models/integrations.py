"""Tabelas de integrações externas (Legal One).

- `legalone_records`: cópia bruta (JSON) de cada entidade lida do Legal One, por tipo e id
  externo. É a fonte para reprocessamento e para o que ainda não tem tabela própria
  (tarefas/prazos, compromissos, contatos que não viram `clients`).
- `legalone_sync_runs`: uma linha por execução do sync, com cursor e estatísticas.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JSONType, TenantModel


class LegalOneRecord(TenantModel):
    __tablename__ = "legalone_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "kind", "external_id", name="uq_legalone_records_ext"),
    )

    kind: Mapped[str] = mapped_column(String(20), index=True)  # lawsuit|contact|update|task|...
    external_id: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    source_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # vínculo com a entidade da plataforma, quando existir (case|client|publication)
    linked_entity: Mapped[str | None] = mapped_column(String(20))
    linked_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)


class LegalOneSyncRun(TenantModel):
    __tablename__ = "legalone_sync_runs"

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    since: Mapped[date | None] = mapped_column(Date)
    resources: Mapped[list] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running|ok|error
    stats: Mapped[dict] = mapped_column(JSONType, default=dict)
    cursor: Mapped[dict] = mapped_column(JSONType, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
