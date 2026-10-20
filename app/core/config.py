"""Configuração via variáveis de ambiente (pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["dev", "test", "staging", "prod"] = "dev"
    app_name: str = "aguia-peregrina"
    secret_key: str = Field(default="dev-only-change-me", min_length=8)
    log_level: str = "INFO"

    database_url: str = "sqlite:///./dev.db"
    db_app_role: str = "aguia_app"

    redis_url: str = "redis://localhost:6379/0"

    workflow_engine: Literal["in_process", "hatchet"] = "in_process"
    hatchet_client_token: str | None = None

    # auto: LiteLLM se instalado; fake: respostas determinísticas (sem chaves); live: força LiteLLM
    llm_mode: Literal["auto", "fake", "live"] = "auto"
    litellm_config: str = "litellm_config.yaml"
    llm_default_model: str = "claude-sonnet"
    llm_small_model: str = "claude-haiku"
    litellm_proxy_url: str | None = None
    litellm_proxy_key: str | None = None
    ops_key: str | None = None  # protege endpoints operacionais (ex.: /health/llm/ping)
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    review_min_seconds_default: int = 600
    review_min_seconds_contestacao: int = 900

    publications_provider: Literal["comunica_pje", "solucionare"] = "comunica_pje"
    solucionare_api_key: str | None = None
    # Chave pública divulgada pelo CNJ (datajud-wiki.cnj.jus.br/api-publica/acesso); o CNJ pode
    # trocá-la a qualquer momento — DATAJUD_API_KEY substitui este padrão sem novo deploy de código.
    datajud_api_key: str | None = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

    # Motor de oportunidades BASA (M12): rodada diária no worker.
    motor_basa_ativo: bool = True
    motor_basa_hora: str = "06:00"  # horário local (America/Belem)
    motor_basa_fuso: str = "America/Belem"
    motor_basa_tenant_nome: str = "FBS — Fonseca Brasil Serrão Advogados"

    # Legal One (Thomson Reuters) — OData somente leitura; credenciais client_credentials
    legalone_client_id: str | None = None
    legalone_client_secret: str | None = None
    legalone_base: str = "https://api.thomsonreuters.com/legalone/v1/api/rest"
    legalone_oauth: str = "https://api.thomsonreuters.com/legalone/oauth"

    s3_endpoint: str | None = None
    s3_bucket: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        """Aceita `postgres://`/`postgresql://` (padrão Railway) e força o driver psycopg3."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return "postgresql+psycopg://" + v[len("postgres://") :]
            if v.startswith("postgresql://"):
                return "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def review_min_seconds(self, draft_type: str) -> int:
        if draft_type == "contestacao":
            return self.review_min_seconds_contestacao
        return self.review_min_seconds_default


@lru_cache
def get_settings() -> Settings:
    return Settings()
