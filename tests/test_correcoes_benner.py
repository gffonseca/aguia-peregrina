"""M14 — fila de correções no Benner: geração com evidência, idempotência, ciclo e confirmação."""

from __future__ import annotations

import io
from datetime import UTC, date, datetime

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.benner import BennerCorrecao
from app.models.faturamento import BasaAtoCobrado, BasaFicha, DataJudProcesso
from app.models.tenant import Tenant
from app.modules.m14_benner import correcoes

ARQ = "08007677620248140073"  # baixado no tribunal, último movimento
REATIVADO = "00000748420168047801"  # baixado, mas andou depois
NAO_ACHADO = "00000793120158044701"
INVALIDO = "00000663320158044701"


def _f(t: Tenant, ficha: str, cnj: str, sit: str = "Em andamento") -> BasaFicha:
    return BasaFicha(
        tenant_id=t.id, ficha=ficha, cnj=cnj, situacao=sit, importado_em=datetime.now(UTC)
    )


def _dj(t: Tenant, cnj: str, movs: list[tuple[int, str, str]]) -> DataJudProcesso:
    return DataJudProcesso(
        tenant_id=t.id,
        cnj=cnj,
        tribunal="X",
        graus={"g1": {"grau": "G1", "movimentos": [[c, n, d, []] for c, n, d in movs]}},
        ultima_movimentacao=max(date.fromisoformat(d) for _, _, d in movs),
        buscado_em=datetime.now(UTC),
    )


def _xlsx(rows: list[list[object]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    for r in rows:
        ws.append(r)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def test_gerar_marcar_e_confirmar(db: Session, as_tenant) -> None:  # type: ignore[no-untyped-def]
    t = Tenant(name="FBS correções", kind="law_firm")
    db.add(t)
    db.commit()
    with as_tenant(t.id):
        db.add_all(
            [
                _f(t, "CIVE.1/2024", ARQ),
                _f(t, "CIVE.2/2016", REATIVADO),
                _f(t, "CIVE.3/2015", NAO_ACHADO),
                _f(t, "CIVE.4/2015", INVALIDO),
                _f(t, "CIVE.5/2015", ARQ[:-1] + "9", "Encerrado"),  # encerrada: fora
                _dj(
                    t, ARQ, [(26, "Distribuição", "2024-05-01"), (246, "Definitivo", "2026-08-10")]
                ),
                _dj(
                    t,
                    REATIVADO,
                    [(246, "Definitivo", "2025-01-10"), (893, "Desarquivamento", "2026-03-01")],
                ),
                BasaAtoCobrado(
                    tenant_id=t.id,
                    competencia="2026-08",
                    cnj="00000000000000000000",
                    ficha="CIVE.999/2020",
                    ato_texto="Petições interlocutórias",
                ),
                BasaAtoCobrado(  # ficha errada, mas o processo existe em outra ficha: não é Benner
                    tenant_id=t.id,
                    competencia="2026-08",
                    cnj=ARQ,
                    ficha="CIVE.888/2020",
                    ato_texto="Petições interlocutórias",
                ),
            ]
        )
        db.commit()

        r = correcoes.gerar(db, t.id)
        assert r == {
            "SITUACAO:novo": 1,
            "NUMERO_PROCESSO:novo": 2,
            "FICHA_INEXISTENTE:novo": 1,
        }
        itens = {(c.tipo, c.ficha): c for c in db.scalars(select(BennerCorrecao))}
        sit = itens[("SITUACAO", "CIVE.1/2024")]
        assert sit.valor_proposto == "Encerrado" and "10/08/2026" in (sit.evidencia or "")
        assert itens[("NUMERO_PROCESSO", "CIVE.4/2015")].confianca == "alta"  # dígito errado
        assert itens[("NUMERO_PROCESSO", "CIVE.3/2015")].confianca == "media"  # não achado
        assert ("SITUACAO", "CIVE.2/2016") not in itens  # andou depois da baixa

        # idempotente e não reabre o que foi tratado
        correcoes.marcar(db, sit.id, "feito", "ana@fbs")
        assert correcoes.gerar(db, t.id) == {
            "SITUACAO:mantido": 1,
            "NUMERO_PROCESSO:atualizado": 2,
            "FICHA_INEXISTENTE:atualizado": 1,
        }
        try:
            correcoes.marcar(db, itens[("NUMERO_PROCESSO", "CIVE.3/2015")].id, "nao_procede", "x")
            raise AssertionError("deveria exigir motivo")
        except ValueError:
            pass

        # o export seguinte mostra a ficha encerrada → confirmado
        from app.modules.m12_faturamento.servico import importar_fichas

        out = importar_fichas(
            db,
            t.id,
            [
                _xlsx(
                    [
                        ["Ficha", "Nº processo principal", "Situação"],
                        ["CIVE.1/2024", "0800767-76.2024.8.14.0073", "Encerrado"],
                    ]
                )
            ],
        )
        assert out["correcoes_confirmadas"] == 1
        db.refresh(sit)
        assert sit.status == "confirmado" and sit.aplicado_por == "ana@fbs"

        lst = correcoes.listar(db, status="pendente")
        assert lst["total"] == 3 and lst["resumo"]["SITUACAO"] == {"confirmado": 1}
        assert correcoes.planilha(db)[:2] == b"PK"
