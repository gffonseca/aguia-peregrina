"""Correções no Benner liberadas para o robô: parâmetros e anexo da peça.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

NOVAS_COLUNAS = (
    ("parametros", sa.JSON().with_variant(JSONB(), "postgresql")),
    ("anexo_nome", sa.String(255)),
    ("anexo", sa.LargeBinary()),
)


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("benner_correcoes")}
    for nome, tipo in NOVAS_COLUNAS:
        if nome not in cols:
            op.add_column("benner_correcoes", sa.Column(nome, tipo, nullable=True))


def downgrade() -> None:
    for nome, _ in NOVAS_COLUNAS:
        op.drop_column("benner_correcoes", nome)
