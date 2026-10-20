"""M12 em produção: carteira → prestação → DataJud (simulado) → motor → oportunidades."""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import Any

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.faturamento import DataJudProcesso, MotorOportunidade
from app.models.tenant import Tenant
from app.modules.m12_faturamento import servico

CNJ_A = "0800767-76.2024.8.14.0073"  # TJPA — extinta por abandono, sem recurso
CNJ_B = "0000074-84.2016.8.04.7801"  # TJAM — apelação cobrada


def _xlsx(rows: list[list[Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class FakeDataJud:
    def __init__(self) -> None:
        self.chamadas: list[tuple[str, int, datetime | None]] = []

    def buscar_por_numeros(self, tribunal: str, numeros: Any, desde: Any = None, lote: int = 100):  # type: ignore[no-untyped-def]
        nums = list(numeros)
        self.chamadas.append((tribunal, len(nums), desde))
        if desde is not None:
            return iter(())
        base = {
            "08007677620248140073": (
                "TJPA",
                [
                    (458, "Abandono da causa", "2026-07-02T10:00:00Z", []),
                    (848, "Trânsito em julgado", "2026-07-30T10:00:00Z", []),
                ],
            ),
            "00000748420168047801": (
                "TJAM",
                [
                    (220, "Improcedência", "2026-07-10T10:00:00Z", []),
                ],
            ),
        }
        out = []
        for n in nums:
            if n in base:
                trib, movs = base[n]
                out.append(
                    {
                        "_id": f"{trib}_G1_{n}",
                        "_source": {
                            "numeroProcesso": n,
                            "tribunal": trib,
                            "grau": "G1",
                            "classe": {"nome": "Execução de Título Extrajudicial"},
                            "dataHoraUltimaAtualizacao": "2026-08-01T00:00:00Z",
                            "movimentos": [
                                {
                                    "codigo": c,
                                    "nome": nm,
                                    "dataHora": d,
                                    "complementosTabelados": [{"nome": x} for x in cp],
                                }
                                for c, nm, d, cp in movs
                            ],
                        },
                    }
                )
        return iter(out)


def test_fluxo_completo(db: Session, as_tenant) -> None:  # type: ignore[no-untyped-def]
    t = Tenant(name="FBS teste motor", kind="law_firm")
    db.add(t)
    db.commit()
    with as_tenant(t.id):
        r = servico.importar_fichas(
            db,
            t.id,
            [
                _xlsx(
                    [
                        [
                            "Cadastrado em",
                            "Ficha",
                            "Adverso principal",
                            "Nº processo principal",
                            "Situação",
                            "Valor da causa",
                        ],
                        [datetime(2024, 5, 1), "CIVE.1/2024", "X", CNJ_A, "Em andamento", 1000.0],
                        [datetime(2016, 5, 1), "CIVE.2/2016", "Y", CNJ_B, "Em andamento", 2000.0],
                        [
                            datetime(2016, 5, 1),
                            "CIVE.3/2016",
                            "Z",
                            "0000001-77.2017.8.04.3501",
                            "Encerrado",
                            10.0,
                        ],
                    ]
                )
            ],
        )
        assert r == {"novas": 3, "atualizadas": 0, "total": 3, "correcoes_confirmadas": 0}
        assert len(servico.fichas_ativas(db)) == 2

        pres = servico.importar_prestacao(
            db,
            t.id,
            "2026-07",
            _xlsx(
                [
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
                    ],
                    [
                        "CIVE.2/2016",
                        CNJ_B,
                        "Urucará",
                        "Amazonas",
                        "Execução",
                        "Y",
                        "Recursos apelação, adesivo, ordinário, inominado.",
                        "2026-07-25",
                        250,
                    ],
                ]
            ),
        )
        assert pres["linhas"] == 1
        assert servico.cobertura_das_prestacoes(db) == (date(2026, 7, 1), date(2026, 7, 31))

        fake = FakeDataJud()
        s1 = servico.sincronizar_datajud(db, t.id, fake, hoje=date(2026, 10, 20))  # type: ignore[arg-type]
        assert s1["processos_atualizados"] == 2
        assert {c[0] for c in fake.chamadas} == {"tjpa", "tjam"}
        p = db.scalar(select(DataJudProcesso).where(DataJudProcesso.cnj == "08007677620248140073"))
        assert p is not None and p.ultima_movimentacao == date(2026, 7, 30)

        # segunda busca é incremental (com `desde`) para quem já foi buscado
        fake2 = FakeDataJud()
        servico.sincronizar_datajud(db, t.id, fake2, hoje=date(2026, 10, 21))  # type: ignore[arg-type]
        assert all(c[2] is not None for c in fake2.chamadas if c[1])

        ex = servico.rodar_motor(db, t.id, hoje=date(2026, 10, 20))
        assert ex.status == "ok" and ex.relatorio_xlsx
        ops = {(o.cnj, o.evento): o for o in db.scalars(select(MotorOportunidade))}
        abandono = ops[("08007677620248140073", "sentenca_desfavoravel")]
        assert abandono.status == "ABERTA"  # janela vai além da cobertura (jul/26)
        improc = ops[("00000748420168047801", "sentenca_desfavoravel")]
        assert improc.status == "ATENDIDA" and improc.ficha == "CIVE.2/2016"
        assert ex.estatisticas["carteira_ativa"] == 2
