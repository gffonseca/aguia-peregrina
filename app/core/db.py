"""Engine, sessão e base declarativa do SQLAlchemy 2."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings
from app.core.tenancy import current_tenant_id


class Base(DeclarativeBase):
    pass


def _make_engine() -> Any:
    settings = get_settings()
    kwargs: dict[str, Any] = {"pool_pre_ping": True, "future": True}
    if settings.is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(settings.database_url, **kwargs)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@event.listens_for(SessionLocal, "after_begin")
def _set_tenant_guc(session: Session, transaction: Any, connection: Any) -> None:
    """Propaga o tenant corrente para o Postgres (GUC `app.tenant_id`) a cada transação.

    As policies de RLS criadas na migração inicial usam
    `current_setting('app.tenant_id', true)`; sem o GUC nenhuma linha é visível.
    Em SQLite (testes) o filtro é aplicado em Python (ver tenancy.TenantQuery).
    """
    if connection.dialect.name != "postgresql":
        return
    tenant_id = current_tenant_id.get()
    if tenant_id is not None:
        connection.execute(
            text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant_id)}
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
