"""Sentry no web e no worker (desligado sem SENTRY_DSN).

Sem envio de dados pessoais por padrão (`send_default_pii=False`) e sem corpo de request:
processos, partes e e-mails não vão para o Sentry; só a pilha do erro e o contexto técnico.
"""

from __future__ import annotations

import logging

from app.core.config import get_settings

log = logging.getLogger(__name__)


def iniciar_sentry(componente: str) -> bool:
    s = get_settings()
    if not s.sentry_dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:  # pragma: no cover
        log.warning("SENTRY_DSN definido mas sentry-sdk não instalado")
        return False
    sentry_sdk.init(
        dsn=s.sentry_dsn,
        environment=s.app_env,
        send_default_pii=False,
        max_request_body_size="never",
        traces_sample_rate=s.sentry_traces_rate,
    )
    sentry_sdk.set_tag("componente", componente)
    return True
