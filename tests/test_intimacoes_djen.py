"""DJEN (Comunica PJe): paginação, mapeamento e entrada na triagem (carteira BASA + OAB)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.publications.comunica_pje import ComunicaPjeProvider
from app.models.faturamento import BasaFicha
from app.models.tenant import Tenant
from app.models.triagem import TriagemEmail
from app.modules.m13_triagem.servico import sincronizar_intimacoes

BASA = "00000720320168045801"


def _item(i: int, num: str, texto: str) -> dict[str, object]:
    return {
        "id": i,
        "data_disponibilizacao": "2026-10-19",
        "siglaTribunal": "TJAM",
        "tipoComunicacao": "Intimação",
        "nomeClasse": "Execução de Título Extrajudicial",
        "nomeOrgao": "2ª Vara de Maués",
        "texto": texto,
        "numero_processo": num,
        "link": f"https://comunica.pje.jus.br/x/{i}",
    }


def _provider() -> tuple[ComunicaPjeProvider, list[dict[str, str]]]:
    vistos: list[dict[str, str]] = []

    def h(req: httpx.Request) -> httpx.Response:
        q = dict(req.url.params)
        vistos.append(q)
        if q.get("nomeParte"):
            if q["pagina"] == "1":
                itens = [_item(1, BASA, "Fica a parte intimada da prescrição intercorrente")]
                itens += [_item(100 + k, "00000000000000000001", "outro") for k in range(99)]
                return httpx.Response(200, json={"count": 101, "items": itens})
            return httpx.Response(
                200, json={"count": 101, "items": [_item(2, "00000000000000000002", "fora")]}
            )
        return httpx.Response(
            200,
            json={
                "count": 1,
                "items": [_item(3, "01501094020268041000", "Julgo procedente os embargos")],
            },
        )

    return ComunicaPjeProvider(
        client=httpx.Client(transport=httpx.MockTransport(h)), pausa_s=0
    ), vistos


def test_djen_para_triagem(db: Session, as_tenant) -> None:  # type: ignore[no-untyped-def]
    t = Tenant(name="FBS djen", kind="law_firm")
    db.add(t)
    db.commit()
    with as_tenant(t.id):
        db.add(
            BasaFicha(
                tenant_id=t.id,
                ficha="CIVE.018895/2016",
                cnj=BASA,
                situacao="Em andamento",
                importado_em=datetime.now(UTC),
            )
        )
        db.commit()
        prov, vistos = _provider()
        r = sincronizar_intimacoes(
            db, t.id, prov, date(2026, 10, 17), ["12.724/pa"], "BANCO DA AMAZONIA"
        )
        assert r["djen_parte"] == 101 and r["djen_oab"] == 1
        assert r["triagem_novos"] == 2  # só a da carteira (por parte) + a da OAB
        assert {"numeroOab": "12724", "ufOab": "PA"}.items() <= vistos[-1].items()
        itens = {e.mensagem_id: e for e in db.scalars(select(TriagemEmail))}
        basa = itens["djen:1"]
        assert basa.papeis == ["prazos_am"] and basa.fichas == ["CIVE.018895/2016"]
        assert "prescrição" in (basa.acao or "")
        outro = itens["djen:3"]
        assert outro.papeis == ["prazos_escritorio"] and outro.urgencia == "alta"
        # idempotente
        prov2, _ = _provider()
        assert (
            sincronizar_intimacoes(
                db, t.id, prov2, date(2026, 10, 17), ["12724/PA"], "BANCO DA AMAZONIA"
            )["triagem_repetidos"]
            == 2
        )
