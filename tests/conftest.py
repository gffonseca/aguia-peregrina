from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("REVIEW_MIN_SECONDS_DEFAULT", "0")
os.environ.setdefault("REVIEW_MIN_SECONDS_CONTESTACAO", "0")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.tenancy import current_tenant_id, install_tenant_guard
from app.models import Base
from app.models.tenant import Tenant


@pytest.fixture(scope="session")
def engine():  # type: ignore[no-untyped-def]
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session_factory(engine):  # type: ignore[no-untyped-def]
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    install_tenant_guard(factory)
    return factory


@pytest.fixture
def db(session_factory) -> Iterator[Session]:  # type: ignore[no-untyped-def]
    s = session_factory()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture
def two_tenants(db: Session) -> tuple[uuid.UUID, uuid.UUID]:
    a = Tenant(name="FBS Advogados", kind="law_firm")
    b = Tenant(name="Compradora Norte", kind="credit_buyer")
    db.add_all([a, b])
    db.commit()
    return a.id, b.id


@pytest.fixture
def as_tenant():  # type: ignore[no-untyped-def]
    class _Ctx:
        def __init__(self, tid: uuid.UUID | None) -> None:
            self.tid = tid

        def __enter__(self):  # type: ignore[no-untyped-def]
            self.token = current_tenant_id.set(self.tid)
            return self

        def __exit__(self, *exc):  # type: ignore[no-untyped-def]
            current_tenant_id.reset(self.token)

    return _Ctx
