"""Rodada do motor de oportunidades BASA: DataJud incremental + detecção + relatório.

Payload: `{"tenant_id": uuid, "completo": bool (busca tudo no DataJud), "hoje": "AAAA-MM-DD"}`.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Any

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.tenancy import current_tenant_id
from app.integrations.datajud.client import DataJudClient
from app.modules.m12_faturamento.servico import rodar_motor, sincronizar_datajud

log = logging.getLogger(__name__)


def run(payload: dict[str, Any], *, client: DataJudClient | None = None) -> dict[str, Any]:
    tenant_id = uuid.UUID(str(payload["tenant_id"]))
    hoje = date.fromisoformat(payload["hoje"]) if payload.get("hoje") else date.today()
    token = current_tenant_id.set(tenant_id)
    try:
        with SessionLocal() as db:
            dj = client or DataJudClient(get_settings().datajud_api_key)
            sync = sincronizar_datajud(
                db, tenant_id, dj, completo=bool(payload.get("completo")), hoje=hoje
            )
            log.info("motor_basa datajud %s", sync)
            ex = rodar_motor(db, tenant_id, hoje=hoje)
            est = {k: v for k, v in (ex.estatisticas or {}).items() if k != "por_evento"}
            log.info("motor_basa ok execucao=%s %s", ex.id, est)
            return {"execucao_id": str(ex.id), "datajud": sync, **est}
    finally:
        current_tenant_id.reset(token)
