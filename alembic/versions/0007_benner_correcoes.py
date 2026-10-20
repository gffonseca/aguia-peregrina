"""Fila de correções no Benner (assistida e, depois, pelo robô).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-20

Mesmo padrão da 0006: cria só o que faltar e aplica RLS/grants às tabelas novas no Postgres.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models import Base

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

APP_ROLE = "aguia_app"
NEW_TABLES = ("benner_correcoes",)


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    missing = [Base.metadata.tables[t] for t in NEW_TABLES if t not in existing]
    if missing:
        Base.metadata.create_all(bind=bind, tables=missing)
    if bind.dialect.name != "postgresql":
        return
    for table in NEW_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
                USING (tenant_id = app_current_tenant())
                WITH CHECK (tenant_id = app_current_tenant())
            """
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {APP_ROLE}")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in NEW_TABLES:
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
