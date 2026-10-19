"""Schema inicial com tenant_id em todas as tabelas e policies de RLS.

Revision ID: 0001
Revises:
Create Date: 2026-10-19

Estratégia:
- Tabelas criadas a partir de `Base.metadata` (fonte única: app/models).
- Em Postgres: extensão pgvector, coluna `embedding vector(1536)` em document_pages,
  role de aplicação sem BYPASSRLS, `ENABLE/FORCE ROW LEVEL SECURITY` e policy
  `tenant_isolation` em toda tabela com `tenant_id`, baseada no GUC `app.tenant_id`
  (definido por transação em app/core/db.py). `tenants` só expõe a própria linha.
- `audit_log` é append-only para a role da aplicação (sem UPDATE/DELETE).
- Em SQLite (testes) só cria as tabelas.
"""

from __future__ import annotations

from alembic import op

from app.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

APP_ROLE = "aguia_app"


def _tenant_tables() -> list[str]:
    return sorted(
        t.name for t in Base.metadata.sorted_tables if "tenant_id" in t.c and t.name != "tenants"
    )


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    if is_pg:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    Base.metadata.create_all(bind=bind)

    if not is_pg:
        return

    op.execute("ALTER TABLE document_pages ADD COLUMN IF NOT EXISTS embedding vector(1536)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_pages_embedding ON document_pages "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
                CREATE ROLE {APP_ROLE} NOLOGIN NOBYPASSRLS;
            END IF;
        END $$;
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")

    # Função utilitária: tenant corrente (NULL se não definido → nenhuma linha visível)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_tenant() RETURNS uuid
        LANGUAGE sql STABLE AS $$
            SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid
        $$;
        """
    )

    for table in _tenant_tables():
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
        privileges = "SELECT, INSERT" if table == "audit_log" else "SELECT, INSERT, UPDATE, DELETE"
        op.execute(f"GRANT {privileges} ON {table} TO {APP_ROLE}")

    # tenants: a aplicação só enxerga a própria linha
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_self ON tenants")
    op.execute("CREATE POLICY tenant_self ON tenants USING (id = app_current_tenant())")
    op.execute(f"GRANT SELECT, UPDATE ON tenants TO {APP_ROLE}")

    # Trigger: audit_log imutável mesmo para quem tiver UPDATE/DELETE
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_log_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log é append-only';
        END $$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_audit_log_immutable ON audit_log")
    op.execute(
        "CREATE TRIGGER trg_audit_log_immutable BEFORE UPDATE OR DELETE ON audit_log "
        "FOR EACH ROW EXECUTE FUNCTION audit_log_immutable()"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_log_immutable ON audit_log")
        op.execute("DROP FUNCTION IF EXISTS audit_log_immutable()")
        for table in _tenant_tables():
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute("DROP POLICY IF EXISTS tenant_self ON tenants")
        op.execute("DROP FUNCTION IF EXISTS app_current_tenant()")
    Base.metadata.drop_all(bind=bind)
