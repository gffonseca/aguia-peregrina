"""Isolamento entre tenants na camada da aplicação (o RLS do Postgres é a segunda camada)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.tenancy import TenantIsolationError
from app.models.litigation import Case


def test_select_is_scoped_to_current_tenant(db, two_tenants, as_tenant) -> None:  # type: ignore[no-untyped-def]
    a, b = two_tenants
    with as_tenant(a):
        db.add(Case(cnj_number="0000001-11.2026.8.14.0301", tenant_id=a))
        db.commit()
    with as_tenant(b):
        db.add(Case(cnj_number="0000002-22.2026.8.14.0301", tenant_id=b))
        db.commit()

    with as_tenant(a):
        rows = list(db.scalars(select(Case)))
        assert {r.tenant_id for r in rows} == {a}
        assert all(r.cnj_number.startswith("0000001") for r in rows)

    with as_tenant(b):
        rows = list(db.scalars(select(Case)))
        assert {r.tenant_id for r in rows} == {b}

    with as_tenant(None):
        # sem tenant no contexto não há filtro automático: a aplicação nunca deve operar assim
        rows = list(db.scalars(select(Case)))
        assert {r.tenant_id for r in rows} >= {a, b}


def test_tenant_id_is_filled_from_context(db, two_tenants, as_tenant) -> None:  # type: ignore[no-untyped-def]
    a, _ = two_tenants
    with as_tenant(a):
        case = Case(cnj_number="0000003-33.2026.8.14.0301")
        db.add(case)
        db.commit()
        assert case.tenant_id == a


def test_cross_tenant_write_is_blocked(db, two_tenants, as_tenant) -> None:  # type: ignore[no-untyped-def]
    a, b = two_tenants
    with as_tenant(a):
        db.add(Case(cnj_number="0000004-44.2026.8.14.0301", tenant_id=b))
        with pytest.raises(TenantIsolationError):
            db.commit()
        db.rollback()


def test_get_by_id_from_other_tenant_is_invisible(db, two_tenants, as_tenant) -> None:  # type: ignore[no-untyped-def]
    a, b = two_tenants
    with as_tenant(a):
        case = Case(cnj_number="0000005-55.2026.8.14.0301")
        db.add(case)
        db.commit()
        case_id = case.id
    db.expunge_all()
    with as_tenant(b):
        assert db.scalar(select(Case).where(Case.id == case_id)) is None


def test_rls_migration_covers_every_tenant_table() -> None:
    """Toda tabela com tenant_id (exceto tenants) deve entrar na policy da migração inicial."""
    import importlib.util
    from pathlib import Path

    from app.models import Base

    path = (
        Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0001_initial_schema_rls.py"
    )
    spec = importlib.util.spec_from_file_location("m0001", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    covered = set(mod._tenant_tables())
    expected = {t.name for t in Base.metadata.sorted_tables if "tenant_id" in t.c} - {"tenants"}
    assert covered == expected
    assert "users" in covered and "audit_log" in covered and "llm_calls" in covered


def test_uuid_tenants_are_distinct(two_tenants) -> None:  # type: ignore[no-untyped-def]
    a, b = two_tenants
    assert isinstance(a, uuid.UUID) and a != b
