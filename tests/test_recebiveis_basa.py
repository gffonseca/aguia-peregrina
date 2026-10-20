"""Recebíveis BASA: dias úteis, vencimento (cl. 18ª), alertas, minuta e fluxo pela API."""

from __future__ import annotations

import io
from datetime import date

from openpyxl import Workbook

from app.modules.m12_faturamento.recebiveis import (
    Recebivel,
    dias_uteis_entre,
    feriados,
    situacao,
    vencimento_contratual,
)


def test_feriados_e_vencimento_contratual() -> None:
    f = feriados(2026)
    assert date(2026, 4, 3) in f  # Sexta-feira Santa (Páscoa 05/04/2026)
    assert date(2026, 2, 16) in f and date(2026, 2, 17) in f  # Carnaval
    assert date(2026, 6, 4) in f  # Corpus Christi
    assert date(2026, 8, 15) in f  # Adesão do Pará
    assert vencimento_contratual("2026-07") == date(2026, 8, 14)
    assert vencimento_contratual("2026-08") == date(2026, 9, 15)  # 07/09 no meio
    assert vencimento_contratual("2026-09") == date(2026, 10, 15)  # 12/10 no meio
    assert dias_uteis_entre(date(2026, 10, 15), date(2026, 10, 20)) == 3


def test_etapas_alertas_e_minuta() -> None:
    hoje = date(2026, 10, 20)
    r = Recebivel("2026-10", "PA", valor_faturavel=80_000)
    assert situacao(r, hoje).etapa == "A_ENVIAR" and not situacao(r, hoje).alertas

    r = Recebivel("2026-09", "PA", valor_faturavel=70_000, enviado_em=date(2026, 9, 30))
    s = situacao(r, hoje)
    assert s.etapa == "ENVIADA"
    assert {a.codigo for a in s.alertas} == {"CONFERENCIA_PARADA", "VENCIDO"}
    assert s.minuta and "Cláusula Décima Oitava" in s.minuta and "RASCUNHO" in s.minuta
    assert "conformidade" in s.minuta and "já transcorreu" in s.minuta  # ainda sem NF

    r = Recebivel(
        "2026-09",
        "AM",
        valor_faturavel=74_000,
        enviado_em=date(2026, 9, 30),
        conferido_em=date(2026, 10, 5),
        valor_aprovado=73_500,
        nf_numero="1234",
        nf_emitida_em=date(2026, 10, 6),
        nf_valor=73_500,
        pago_em=date(2026, 10, 14),
        valor_pago=73_500,
    )
    s = situacao(r, hoje)
    assert s.etapa == "PAGA" and s.em_aberto == 0 and s.minuta is None
    assert [a.codigo for a in s.alertas] == ["GLOSA"]

    r.valor_pago = 70_000
    s = situacao(r, hoje)
    assert "PAGO_A_MENOR" in {a.codigo for a in s.alertas} and s.em_aberto == 3_500
    assert s.minuta and "Nota Fiscal nº 1234" in s.minuta


def test_fluxo_api_recebiveis(engine, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from app.core import db as core_db
    from app.core.config import get_settings
    from app.main import app

    core_db.SessionLocal.configure(bind=engine)
    monkeypatch.setattr(get_settings(), "ops_key", "k")
    c = TestClient(app)
    tid = c.post("/faturamento/basa/setup", headers={"X-Ops-Key": "k"}).json()["tenant_id"]
    h = {"X-Ops-Key": "k", "X-Tenant-ID": tid, "X-Usuario": "Teste"}

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(
        [
            "NPC",
            "Nº Processo",
            "Comarca",
            "UF",
            "Ação",
            "Parte Adversa",
            "Ato processual realizado",
            "Data do protocolo",
            "Valor",
        ]
    )
    ws.append(
        [
            "CIVE.1/2015",
            "0000066-32.2015.8.04.4701",
            "Itacoatiara",
            "Amazonas",
            "Execução",
            "X",
            "Petições interlocutórias",
            "2026-09-10",
            120,
        ]
    )
    ws.append(
        [
            "CIVE.2/2015",
            "0000079-31.2015.8.04.4701",
            "Belém",
            "Pará",
            "Execução",
            "Y",
            "Recursos apelação",
            "2026-09-11",
            250,
        ]
    )
    b = io.BytesIO()
    wb.save(b)
    r = c.post(
        "/faturamento/basa/prestacoes?competencia=2026-09",
        headers=h,
        files={"arquivo": ("p.xlsx", b.getvalue())},
    )
    assert r.status_code == 200, r.text

    lista = c.get("/faturamento/basa/recebiveis", headers=h).json()
    assert {(i["uf"], i["valor_faturavel"]) for i in lista["itens"]} == {
        ("AM", 120.0),
        ("PA", 250.0),
    }
    pa = next(i for i in lista["itens"] if i["uf"] == "PA")
    r = c.patch(
        f"/faturamento/basa/recebiveis/{pa['id']}",
        headers=h,
        json={"enviado_em": "2026-09-30", "nf_numero": "77", "nf_valor": "250"},
    )
    assert r.status_code == 200, r.text
    it = r.json()
    assert it["enviado_em"] == "2026-09-30" and it["nf_valor"] == 250.0
    assert [x["campo"] for x in it["historico"]] == ["enviado_em", "nf_numero", "nf_valor"]
    assert it["historico"][0]["por"] == "Teste"
    assert (
        c.patch(
            f"/faturamento/basa/recebiveis/{pa['id']}", headers=h, json={"uf": "AM"}
        ).status_code
        == 422
    )

    # reimportar a competência preserva o lançamento manual
    c.post(
        "/faturamento/basa/prestacoes?competencia=2026-09",
        headers=h,
        files={"arquivo": ("p.xlsx", b.getvalue())},
    )
    pa2 = next(
        i
        for i in c.get("/faturamento/basa/recebiveis", headers=h).json()["itens"]
        if i["uf"] == "PA"
    )
    assert pa2["id"] == pa["id"] and pa2["nf_numero"] == "77"

    pg = c.get("/painel/recebiveis")
    assert pg.status_code == 200 and "Recebíveis BASA" in pg.text
