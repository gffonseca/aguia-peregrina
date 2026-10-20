"""Entrypoint do processo `worker` (Procfile/Railway).

Com Hatchet configurado, sobe o worker Hatchet. Sem ele (engine in_process), roda o agendador
diário: o motor de oportunidades BASA no horário `MOTOR_BASA_HORA` (fuso `MOTOR_BASA_FUSO`),
uma vez por dia, para o tenant `MOTOR_BASA_TENANT_NOME`. Se o worker reiniciar depois do
horário e a rodada do dia ainda não tiver acontecido, ela roda na hora.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.tenancy import current_tenant_id
from app.models.faturamento import MotorExecucao
from app.models.tenant import Tenant
from app.workflows.engine import HatchetEngine, get_engine
from app.workflows.jobs import motor_basa

log = logging.getLogger("aguia.worker")


def _tenant_id() -> str | None:
    nome = get_settings().motor_basa_tenant_nome
    with SessionLocal() as db:
        t = db.scalar(select(Tenant).where(Tenant.name == nome, Tenant.is_active.is_(True)))
    return str(t.id) if t else None


def _ja_rodou_hoje(tenant_id: str, hoje: str) -> bool:
    import uuid

    token = current_tenant_id.set(uuid.UUID(tenant_id))
    try:
        with SessionLocal() as db:
            # qualquer status conta (inclusive erro): evita repetir a cada minuto uma rodada que
            # falha; a nova tentativa é manual (POST /faturamento/basa/motor/rodar).
            ex = db.scalar(
                select(MotorExecucao)
                .where(MotorExecucao.status.in_(("ok", "erro", "rodando")))
                .order_by(MotorExecucao.iniciado_em.desc())
            )
            return bool(ex and ex.referencia.isoformat() == hoje)
    finally:
        current_tenant_id.reset(token)


def _pegar_pedido(tenant_id: str) -> dict[str, object] | None:
    """Pedido manual (POST /faturamento/basa/motor/rodar) ainda não atendido."""
    import uuid

    token = current_tenant_id.set(uuid.UUID(tenant_id))
    try:
        with SessionLocal() as db:
            p = db.scalar(
                select(MotorExecucao)
                .where(MotorExecucao.status == "pedido")
                .order_by(MotorExecucao.iniciado_em)
            )
            if p is None:
                return None
            p.status = "atendido"
            db.commit()
            return dict(p.estatisticas or {})
    finally:
        current_tenant_id.reset(token)


def ciclo(agora: datetime) -> bool:
    """Uma verificação do agendador; devolve True se rodou o motor."""
    s = get_settings()
    if not s.motor_basa_ativo:
        return False
    tid = _tenant_id()
    if not tid:
        return False
    hoje = agora.date().isoformat()
    pedido = _pegar_pedido(tid)
    if pedido is None:
        hh, mm = (int(x) for x in s.motor_basa_hora.split(":"))
        if (agora.hour, agora.minute) < (hh, mm) or _ja_rodou_hoje(tid, hoje):
            return False
    completo = bool(pedido and pedido.get("completo"))
    log.info("motor_basa: rodada de %s (%s)", hoje, "pedido manual" if pedido else "agendada")
    try:
        r = motor_basa.run({"tenant_id": tid, "hoje": hoje, "completo": completo})
        log.info("motor_basa: concluído %s", r)
    except Exception:  # não derruba o worker; a execução fica gravada com status=erro
        log.exception("motor_basa: falhou")
    return True


def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    engine = get_engine()
    if isinstance(engine, HatchetEngine):  # pragma: no cover
        log.info("iniciando worker Hatchet")
        engine.worker().start()
        return
    fuso = ZoneInfo(get_settings().motor_basa_fuso)
    log.info(
        "worker in_process: agendador diário do motor BASA às %s (%s)",
        get_settings().motor_basa_hora,
        get_settings().motor_basa_fuso,
    )
    while True:
        try:
            ciclo(datetime.now(fuso))
        except Exception:
            log.exception("agendador: erro na verificação")
        time.sleep(60)


if __name__ == "__main__":
    main()
