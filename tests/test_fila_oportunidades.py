"""Fila de atos por pessoa e decisões que o motor respeita nas rodadas seguintes."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from app.models.faturamento import MotorExecucao, MotorOportunidade
from app.modules.m12_faturamento.deteccao import Oportunidade
from app.modules.m12_faturamento.fila import aplicar_decisoes

PA = "08007677620248140073"
AM = "00000748420168047801"


def _op(ex: MotorExecucao, cnj: str, evento: str, status: str = "ABERTA", **kw: object):  # type: ignore[no-untyped-def]
    base: dict[str, object] = dict(
        tenant_id=ex.tenant_id,
        execucao_id=ex.id,
        cnj=cnj,
        ficha="CIVE.1",
        evento=evento,
        data_evento=date(2026, 9, 1),
        ato_id="apelacao",
        valor=250.0,
        papel="redige",
        prazo=date(2026, 10, 10),
        confianca="alta",
        status=status,
    )
    base.update(kw)
    return MotorOportunidade(**base)


def test_aplicar_decisoes_no_motor() -> None:
    class D:  # decisões simuladas
        pass

    o1 = Oportunidade(
        PA,
        "sentenca_desfavoravel",
        date(2026, 9, 1),
        "apelacao",
        250,
        "redige",
        None,
        "alta",
        "",
        "",
    )
    o2 = Oportunidade(
        AM,
        "sentenca_desfavoravel",
        date(2026, 9, 1),
        "apelacao",
        250,
        "redige",
        None,
        "alta",
        "",
        "",
    )

    class FakeDB:
        def scalars(self, _q):  # type: ignore[no-untyped-def]
            d1, d2 = D(), D()
            d1.cnj, d1.evento, d1.data_evento, d1.decisao, d1.por = (
                PA,
                o1.evento,
                o1.data_evento,
                "feito",
                "ana",
            )  # type: ignore[attr-defined]
            d2.cnj, d2.evento, d2.data_evento, d2.decisao, d2.por = (
                AM,
                o2.evento,
                o2.data_evento,
                "nao_cabe",
                "bia",
            )  # type: ignore[attr-defined]
            return [d1, d2]

    assert aplicar_decisoes(FakeDB(), [o1, o2]) == 2  # type: ignore[arg-type]
    assert (o1.status, o2.status) == ("ATENDIDA", "DESCARTADA")


def test_fila_por_uf_e_decisao_via_api(engine, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from app.core import db as core_db
    from app.core.config import get_settings
    from app.core.tenancy import current_tenant_id
    from app.main import app

    core_db.SessionLocal.configure(bind=engine)
    monkeypatch.setattr(get_settings(), "ops_key", "k")
    c = TestClient(app)
    tid = c.post("/faturamento/basa/setup", headers={"X-Ops-Key": "k"}).json()["tenant_id"]
    h = {"X-Ops-Key": "k", "X-Tenant-ID": tid, "X-Usuario": "ana@fbs.test"}

    tok = current_tenant_id.set(uuid.UUID(tid))
    try:
        with core_db.SessionLocal() as db:
            ex = MotorExecucao(
                tenant_id=uuid.UUID(tid),
                iniciado_em=datetime.now(UTC),
                referencia=date(2026, 10, 20),
                status="ok",
            )
            db.add(ex)
            db.commit()
            db.add_all(
                [
                    _op(ex, PA, "sentenca_desfavoravel"),
                    _op(ex, AM, "sentenca_desfavoravel", prazo=date(2026, 11, 30)),
                    _op(
                        ex,
                        PA,
                        "processo_sem_evento_90_dias",
                        data_evento=date(2025, 1, 1),
                        ato_id="peticao_interlocutoria",
                        valor=120.0,
                    ),
                    _op(
                        ex,
                        "08000010020248140073",
                        "processo_sem_evento_90_dias",
                        data_evento=date(2024, 1, 1),
                        ato_id="peticao_interlocutoria",
                        valor=120.0,
                    ),
                    _op(ex, PA, "recurso_juntado", status="ALERTA"),
                    _op(ex, PA, "arquivamento_definitivo", status="ALERTA"),
                ]
            )
            db.commit()
    finally:
        current_tenant_id.reset(tok)

    c.put("/triagem/papeis/equipe_pa", headers=h, json=[{"nome": "Ana", "email": "ana@fbs.test"}])
    g = c.get("/faturamento/basa/fila?pessoa=ana@fbs.test", headers=h).json()
    assert g["ufs"] == ["PA"] and g["total"] == 1
    assert g["itens"][0]["prazo_passou"] is (date(2026, 10, 10) < date.today())
    tudo = c.get("/faturamento/basa/fila", headers=h).json()
    assert tudo["total"] == 2 and tudo["valor_total"] == 500.0

    al = c.get("/faturamento/basa/fila?tipo=alertas", headers=h).json()
    assert [i["evento"] for i in al["itens"]] == ["recurso_juntado"]  # arquivamento fica fora
    par = c.get("/faturamento/basa/fila?tipo=parados", headers=h).json()
    assert [i["data_evento"] for i in par["itens"]] == ["2024-01-01", "2025-01-01"]

    it = g["itens"][0]
    r = c.post(
        "/faturamento/basa/fila/decisao",
        headers=h,
        json={
            "processo": it["processo"],
            "evento": it["evento"],
            "data_evento": it["data_evento"],
            "decisao": "feito",
            "observacao": "protocolo 123",
        },
    )
    assert r.status_code == 200 and r.json()["por"] == "ana@fbs.test"
    assert c.get("/faturamento/basa/fila?pessoa=ana@fbs.test", headers=h).json()["total"] == 0
    dec = c.get(
        "/faturamento/basa/fila?pessoa=ana@fbs.test&incluir_decididas=true", headers=h
    ).json()
    assert (
        dec["itens"][0]["decisao"] == "feito" and dec["itens"][0]["decisao_obs"] == "protocolo 123"
    )
    # desfazer
    c.post(
        "/faturamento/basa/fila/decisao",
        headers=h,
        json={
            "processo": it["processo"],
            "evento": it["evento"],
            "data_evento": it["data_evento"],
            "decisao": None,
        },
    )
    assert c.get("/faturamento/basa/fila?pessoa=ana@fbs.test", headers=h).json()["total"] == 1
    bad = c.post(
        "/faturamento/basa/fila/decisao",
        headers=h,
        json={
            "processo": it["processo"],
            "evento": it["evento"],
            "data_evento": it["data_evento"],
            "decisao": "talvez",
        },
    )
    assert bad.status_code == 422
    assert c.get("/painel/oportunidades").status_code == 200
