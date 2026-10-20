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


def _pegar_pedido(tenant_id: str) -> tuple[str, dict[str, object]] | None:
    """Pedido manual (POST /faturamento/basa/motor/rodar) ainda não atendido. Fica como
    'executando' até terminar: se o worker reiniciar no meio, `retomar_interrompidas` o devolve
    à fila."""
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
            p.status = "executando"
            db.commit()
            return str(p.id), dict(p.estatisticas or {})
    finally:
        current_tenant_id.reset(token)


def _encerrar_pedido(tenant_id: str, pedido_id: str) -> None:
    import uuid

    token = current_tenant_id.set(uuid.UUID(tenant_id))
    try:
        with SessionLocal() as db:
            p = db.get(MotorExecucao, uuid.UUID(pedido_id))
            if p is not None:
                p.status = "atendido"
                db.commit()
    finally:
        current_tenant_id.reset(token)


def retomar_interrompidas(tenant_id: str) -> dict[str, int]:
    """Na subida do worker (deploy/reinício): pedido que estava executando volta para a fila;
    rodada que ficou 'rodando' vira 'interrompida' — e não conta como 'já rodou hoje', então a
    rodada diária acontece de novo."""
    import uuid

    token = current_tenant_id.set(uuid.UUID(tenant_id))
    try:
        with SessionLocal() as db:
            n_p = n_r = 0
            for e in db.scalars(
                select(MotorExecucao).where(MotorExecucao.status.in_(("executando", "rodando")))
            ):
                if e.status == "executando":
                    e.status, n_p = "pedido", n_p + 1
                else:
                    e.status, e.erro, n_r = "interrompida", "worker reiniciado no meio", n_r + 1
            db.commit()
            return {"pedidos_retomados": n_p, "rodadas_interrompidas": n_r}
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
    pegou = _pegar_pedido(tid)
    pedido = pegou[1] if pegou else None
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
    finally:
        if pegou:
            _encerrar_pedido(tid, pegou[0])
    return True


_ULTIMA_TRIAGEM: dict[str, datetime] = {}


def ciclo_triagem(agora: datetime) -> bool:
    """Lê a caixa basa@ a cada TRIAGEM_INTERVALO_MIN; desligado sem a configuração do Graph."""
    import uuid

    from app.integrations.msgraph.client import GraphMailClient
    from app.modules.m13_triagem.servico import sincronizar_caixa

    s = get_settings()
    if not (
        s.triagem_caixa and s.msgraph_tenant_id and s.msgraph_client_id and s.msgraph_client_secret
    ):
        return False
    ult = _ULTIMA_TRIAGEM.get("caixa")
    if ult and (agora - ult).total_seconds() < s.triagem_intervalo_min * 60:
        return False
    tid = _tenant_id()
    if not tid:
        return False
    _ULTIMA_TRIAGEM["caixa"] = agora
    cli = GraphMailClient(s.msgraph_tenant_id, s.msgraph_client_id, s.msgraph_client_secret)
    token = current_tenant_id.set(uuid.UUID(tid))
    try:
        with SessionLocal() as db:
            r = sincronizar_caixa(db, uuid.UUID(tid), cli, s.triagem_caixa)
        log.info("triagem: %s", r)
    except Exception:
        log.exception("triagem: falhou")
    finally:
        current_tenant_id.reset(token)
    return True


def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    from app.core.observabilidade import iniciar_sentry

    iniciar_sentry("worker")
    try:
        tid = _tenant_id()
        if tid:
            log.info("worker: retomada %s", retomar_interrompidas(tid))
    except Exception:
        log.exception("worker: falha ao retomar rodadas interrompidas")
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
        try:
            ciclo_triagem(datetime.now(fuso))
        except Exception:
            log.exception("triagem: erro na verificação")
        time.sleep(60)


if __name__ == "__main__":
    main()
