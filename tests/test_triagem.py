"""M13 — triagem da caixa basa@: classificação, roteamento, ingestão, Graph e API."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.integrations.msgraph.client import GraphMailClient, para_email
from app.modules.m13_triagem.classificar import Email, classificar

FBS = ["nicolle@fonsecabrasilserrao.com", "gustavo@fonsecabrasilserrao.com"]
CC = [
    "eduardo@fonsecabrasilserrao.com",
    "karime@fonsecabrasilserrao.com",
    "adrian@fonsecabrasilserrao.com",
]

PROJUDI_PRESCRICAO = (
    "PROCESSO JUDICIAL Nº 0000072-03.2016.8.04.5801\nCLASSE PROCESSUAL: Execução de Título "
    "Extrajudicial\nEXEQUENTE(S): BANCO DA AMAZÔNIA BASA\nUma intimação no processo acima "
    "citado, referente à movimentação DETERMINAÇÃO DE SUSPENSÃO OU SOBRESTAMENTO DOS AUTOS EM "
    "RAZÃO DE PRESCRIÇÃO INTERCORRENTE , foi expedida para a parte BANCO DA AMAZÔNIA BASA."
)


def _e(**kw: object) -> Email:
    base: dict[str, object] = dict(id="1", remetente="x@basa.com.br", assunto="", corpo="")
    base.update(kw)
    return Email(**base)  # type: ignore[arg-type]


def test_intimacao_do_tribunal_vai_para_prazos_da_uf_com_urgencia() -> None:
    t = classificar(
        _e(
            remetente="projudi@tjam.jus.br",
            assunto="Nova Intimação - Mensagem automática",
            corpo=PROJUDI_PRESCRICAO,
        )
    )
    assert t.categoria == "INTIMACAO" and t.urgencia == "alta"
    assert t.uf == "AM" and t.papeis == ["prazos_am"]
    assert t.cnjs == ["00000720320168045801"]
    assert "prescrição" in t.acao

    t = classificar(
        _e(
            remetente="projudi@tjam.jus.br",
            assunto="Decurso de prazo de intimação sem cumprimento",
            corpo="PROCESSO JUDICIAL Nº 0000011-59.2016.8.04.7801 ... teve seu decurso de prazo",
        )
    )
    assert t.urgencia == "alta" and "conferir" in t.acao


def test_pedido_de_acesso_ao_benner_e_so_da_coordenacao_e_mede_excesso_de_copia() -> None:
    t = classificar(
        _e(
            remetente="edno.ferraz@basa.com.br",
            assunto="RES: REUINÃO ALINHAMENTO - 21/09 15H - BASA E FBS",
            corpo="Preciso das seguintes informações para criar o usuário para acesso ao Benner",
            para=FBS[:1] + ["bruno@basa.com.br"],
            cc=CC + FBS[1:],
        )
    )
    assert t.categoria == "SISTEMA_BENNER" and t.papeis == ["coordenacao"]
    assert t.internos_copiados == 5 and t.excesso_copia == 4


def test_prestacao_ruido_e_processo() -> None:
    t = classificar(_e(assunto="Glosa na prestação de contas de agosto", corpo="atos glosados"))
    assert t.categoria == "PRESTACAO_CONTAS" and t.urgencia == "alta"
    assert t.papeis == ["financeiro", "coordenacao"]
    assert classificar(_e(remetente="comunicadobasa@basablog.com.br")).categoria == "IGNORAR"
    t = classificar(
        _e(assunto="Subsídio", corpo="favor enviar cálculo do processo 0800767-76.2024.8.14.0073")
    )
    assert t.categoria == "PROCESSO" and t.papeis == ["equipe_pa"] and t.uf == "PA"


def test_para_email_formato_graph() -> None:
    e = para_email(
        {
            "id": "abc",
            "subject": "s",
            "from": {"emailAddress": {"address": "a@basa.com.br"}},
            "toRecipients": [{"emailAddress": {"address": "b@x.com"}}],
            "ccRecipients": [],
            "body": {"contentType": "text", "content": "oi"},
            "receivedDateTime": "2026-10-20T10:00:00Z",
        }
    )
    assert (e.remetente, e.para, e.corpo) == ("a@basa.com.br", ["b@x.com"], "oi")


def test_cliente_graph_pagina_e_so_le() -> None:
    chamadas: list[tuple[str, str]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        chamadas.append((req.method, req.url.path))
        if "oauth2" in req.url.path:
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        if "page2" in str(req.url):
            return httpx.Response(200, json={"value": [{"id": "2", "subject": "b"}]})
        return httpx.Response(
            200,
            json={
                "value": [{"id": "1", "subject": "a"}],
                "@odata.nextLink": "https://graph.microsoft.com/v1.0/page2",
            },
        )

    cli = GraphMailClient("t", "c", "s", http=httpx.Client(transport=httpx.MockTransport(handler)))
    ids = [m.id for m in cli.mensagens("basa@x.com", datetime(2026, 10, 1, tzinfo=UTC))]
    assert ids == ["1", "2"]
    assert all(m in ("GET", "POST") for m, _ in chamadas)
    assert sum(1 for m, _ in chamadas if m == "POST") == 1  # só o token


def test_fluxo_api(engine, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from app.core import db as core_db
    from app.core.config import get_settings
    from app.main import app

    core_db.SessionLocal.configure(bind=engine)
    monkeypatch.setattr(get_settings(), "ops_key", "k")
    c = TestClient(app)
    tid = c.post("/faturamento/basa/setup", headers={"X-Ops-Key": "k"}).json()["tenant_id"]
    h = {"X-Ops-Key": "k", "X-Tenant-ID": tid, "X-Usuario": "nicolle@fonsecabrasilserrao.com"}
    agora = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    msgs = [
        {
            "id": "m1",
            "subject": "Nova Intimação",
            "from": {"emailAddress": {"address": "projudi@tjam.jus.br"}},
            "body": {"content": PROJUDI_PRESCRICAO},
            "receivedDateTime": agora,
        },
        {
            "id": "m2",
            "subject": "Acesso ao Benner",
            "from": {"emailAddress": {"address": "edno@basa.com.br"}},
            "body": {"content": "criar o usuário para acesso ao Benner"},
            "ccRecipients": [{"emailAddress": {"address": x}} for x in CC],
            "receivedDateTime": agora,
        },
        {
            "id": "m3",
            "subject": "Programe-se",
            "from": {"emailAddress": {"address": "comunicadobasa@basablog.com.br"}},
            "body": {"content": "Centro Cultural"},
            "receivedDateTime": agora,
        },
    ]
    r = c.post("/triagem/importar?caixa=basa@x", headers=h, json=msgs)
    assert r.status_code == 200, r.text
    assert r.json()["novos"] == 3
    assert c.post("/triagem/importar?caixa=basa@x", headers=h, json=msgs).json() == {"repetidos": 3}

    c.put(
        "/triagem/papeis/coordenacao",
        headers=h,
        json=[{"nome": "Nicolle", "email": "Nicolle@fonsecabrasilserrao.com"}],
    )
    meu = c.get("/triagem?pessoa=nicolle@fonsecabrasilserrao.com", headers=h).json()
    assert [p["papel"] for p in meu["papeis"]] == ["coordenacao"]
    assert [i["assunto"] for i in meu["papeis"][0]["itens"]] == ["Acesso ao Benner"]
    tudo = c.get("/triagem", headers=h).json()
    assert {p["papel"] for p in tudo["papeis"]} == {"coordenacao", "prazos_am"}
    assert tudo["metricas"]["ignorados"] == 1 and tudo["metricas"]["copias_internas"] == 3

    iid = meu["papeis"][0]["itens"][0]["id"]
    r = c.patch(f"/triagem/{iid}", headers=h, json={"status": "resolvido"})
    assert r.json()["status"] == "resolvido" and r.json()["tratado_por"].startswith("nicolle")
    assert (
        c.get("/triagem?pessoa=nicolle@fonsecabrasilserrao.com", headers=h).json()["papeis"] == []
    )
    assert c.post("/triagem/sincronizar", headers=h).status_code == 409  # sem app configurado
    assert c.get("/painel/triagem").status_code == 200
