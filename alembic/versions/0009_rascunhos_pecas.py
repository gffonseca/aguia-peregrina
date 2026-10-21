"""Rascunhos de peças pela IA + texto integral das intimações do DJEN.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models import Base

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

APP_ROLE = "aguia_app"
NEW_TABLES = ("rascunhos_pecas",)
NOVAS_COLUNAS = (("texto_integral", sa.Text()),)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = set(insp.get_table_names())
    missing = [Base.metadata.tables[t] for t in NEW_TABLES if t not in existing]
    if missing:
        Base.metadata.create_all(bind=bind, tables=missing)
    cols = {c["name"] for c in insp.get_columns("triagem_emails")}
    for nome, tipo in NOVAS_COLUNAS:
        if nome not in cols:
            op.add_column("triagem_emails", sa.Column(nome, tipo, nullable=True))
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
    for nome, _ in NOVAS_COLUNAS:
        op.drop_column("triagem_emails", nome)
    op.drop_table("rascunhos_pecas")
