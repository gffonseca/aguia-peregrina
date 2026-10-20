"""Worker: deploy no meio de uma rodada não perde o pedido nem bloqueia a rodada do dia."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from app.core.tenancy import current_tenant_id
from app.models.faturamento import MotorExecucao


def test_retoma_pedido_e_libera_rodada(engine, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.core import db as core_db
    from app.core.config import get_settings
    from app.models.tenant import Tenant
    from app.workflows import worker

    core_db.SessionLocal.configure(bind=engine)
    nome = "FBS retomada"
    monkeypatch.setattr(get_settings(), "motor_basa_tenant_nome", nome)
    with core_db.SessionLocal() as db:
        t = Tenant(name=nome, kind="law_firm")
        db.add(t)
        db.commit()
        tid = t.id
    tok = current_tenant_id.set(tid)
    try:
        with core_db.SessionLocal() as db:
            agora = datetime.now(UTC)
            db.add_all(
                [
                    MotorExecucao(
                        tenant_id=tid,
                        iniciado_em=agora,
                        referencia=date(2026, 10, 20),
                        status="pedido",
                    ),
                    MotorExecucao(
                        tenant_id=tid,
                        iniciado_em=agora,
                        referencia=date(2026, 10, 20),
                        status="rodando",
                    ),
                ]
            )
            db.commit()
    finally:
        current_tenant_id.reset(tok)

    pegou = worker._pegar_pedido(str(tid))
    assert pegou is not None  # worker pegou o pedido…
    assert worker._ja_rodou_hoje(str(tid), "2026-10-20")  # …e a rodada 'rodando' bloquearia o dia
    # …e o container morreu aqui. Na subida:
    assert worker.retomar_interrompidas(str(tid)) == {
        "pedidos_retomados": 1,
        "rodadas_interrompidas": 1,
    }
    assert not worker._ja_rodou_hoje(str(tid), "2026-10-20")
    pegou2 = worker._pegar_pedido(str(tid))
    assert pegou2 is not None and pegou2[0] == pegou[0]
    worker._encerrar_pedido(str(tid), pegou2[0])
    assert worker._pegar_pedido(str(tid)) is None
    assert uuid.UUID(pegou[0])
