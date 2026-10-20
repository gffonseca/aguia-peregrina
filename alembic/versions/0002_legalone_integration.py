"""Integração Legal One: `cases.typology_hint`, `legalone_records`, `legalone_sync_runs`.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-19

Idempotente: a migração 0001 cria as tabelas a partir de `Base.metadata` (que já inclui as
novas em bancos criados do zero), então aqui só criamos o que faltar e aplicamos RLS/grants
às tabelas novas em Postgres (mesma policy da 0001).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models import Base

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

APP_ROLE = "aguia_app"
NEW_TABLES = ("legalone_records", "legalone_sync_runs")


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    insp = sa.inspect(bind)

    case_cols = {c["name"] for c in insp.get_columns("cases")}
    if "typology_hint" not in case_cols:
        op.add_column("cases", sa.Column("typology_hint", sa.String(60), nullable=True))

    existing = set(insp.get_table_names())
    missing = [Base.metadata.tables[t] for t in NEW_TABLES if t not in existing]
    if missing:
        Base.metadata.create_all(bind=bind, tables=missing)

    if not is_pg:
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
    with op.batch_alter_table("cases") as batch:
        batch.drop_column("typology_hint")
