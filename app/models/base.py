"""Base comum: UUID pk, timestamps, JSON portátil (JSONB no Postgres)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.tenancy import TenantMixin

JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TenantModel(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """Toda tabela de negócio herda daqui: tem `tenant_id` e entra no RLS."""

    __abstract__ = True


__all__ = ["Base", "JSONType", "TenantModel", "TimestampMixin", "UUIDPrimaryKeyMixin", "utcnow"]
