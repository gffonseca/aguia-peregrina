"""M12 — reconhecimento de atos, enquadramento de coluna, pré-auditoria e Anexo II."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook

from app.modules.m12_faturamento.auditoria import FichaBenner, LinhaAto, auditar, resumo
from app.modules.m12_faturamento.planilhas import gerar_excel, ler_atos
from app.modules.m12_faturamento.tabela import carregar_tabela, enquadrar_coluna, reconhecer_ato

CNJ_A = "0000066-32.2015.8.04.4701"
CNJ_B = "0000079-31.2015.8.04.4701"


def _l(**kw: object) -> LinhaAto:
    base: dict[str, object] = dict(
        ficha="CIVE.1/2015",
        cnj=CNJ_A,
        comarca="Itacoatiara",
        uf="Amazonas",
        acao="Execução",
        parte_adversa="X",
        ato_texto="Petições interlocutórias",
        data=date(2026, 7, 10),
        valor=120.0,
    )
    base.update(kw)
    return LinhaAto(**base)  # type: ignore[arg-type]


def _codigos(a: object) -> set[str]:
    return {x.codigo for x in a.achados}  # type: ignore[attr-defined]


def test_tabela_carrega_e_tem_atos_principais() -> None:
    t = carregar_tabela()
    assert t.contrato == "FB1798"
    assert t.atos["peticao_interlocutoria"].valor("rec_cred") == 120
    assert t.atos["juntada_planilha_custas"].valor("demais") == 60
    assert t.atos["contestacao"].valor("rec_cred") is None
    assert t.atos["arresto_penhora"].valor("trabalhista") == 209
    assert t.atos["citacao_efetivada"].resultado


def test_reconhece_grafias_variadas() -> None:
    assert reconhecer_ato("Atos BASA - Petições interlocutórias") == "peticao_interlocutoria"
    assert reconhecer_ato("PePetições interlocutóriasvs") == "peticao_interlocutoria"
    assert reconhecer_ato("Recursos apelação, adesivo, ordinário, iniminado") == "apelacao"
    assert reconhecer_ato("Contrarrazões ao recurso inominado") == "contrarrazoes"
    assert (
        reconhecer_ato("Audiência de conciliação ou inaugural sem instrução")
        == "audiencia_conciliacao"
    )
    assert reconhecer_ato("Impugnação a embargos: à execução") == "impugnacao_embargos_execucao"
    assert (
        reconhecer_ato("Respostas a agravos: inominado ou regimental") == "resposta_agravo_interno"
    )
    assert reconhecer_ato("coisa nenhuma") is None


def test_enquadramento_de_coluna() -> None:
    assert enquadrar_coluna("Execução", "CIVE.1/2020", CNJ_A) == "rec_cred"
    assert enquadrar_coluna("Ação Indenizatória", "CIVE.1/2020", CNJ_A) == "demais"
    assert enquadrar_coluna("Reclamatória", "TRAB.1/2025", "0000505-40.2025.5.08.0010") == (
        "trabalhista"
    )


def test_regras_de_bloqueio_e_alerta() -> None:
    linhas = [
        _l(),  # OK
        _l(data=date(2026, 7, 10)),  # duplicado exato
        _l(ato_texto="Petições interlocutórias", data=date(2026, 7, 20)),  # repetido no mês
        _l(cnj=CNJ_B, ato_texto="Petição de juntada de planilha de débito", valor=120.0),  # acima
        _l(cnj=CNJ_B, ato_texto="Recursos apelação", valor=150.0, data=date(2026, 7, 3)),  # abaixo
        _l(cnj=CNJ_B, ato_texto="Petição de ciência de intimação", data=date(2026, 7, 4)),
        _l(cnj=CNJ_B, ato_texto="Interlocutória", data=date(2026, 8, 1)),  # fora do mês
        _l(cnj=CNJ_B, ato_texto="Algo sem tabela", data=date(2026, 7, 5)),
        _l(
            cnj=CNJ_B,
            acao="Cobrança",
            ato_texto="Contestação ou defesa",
            valor=250.0,
            data=date(2026, 7, 6),
        ),  # coluna presumida (Banco réu)
    ]
    a = auditar(linhas, "2026-07")
    assert a[0].status == "ALERTA" and "REPETIDO_NO_MES" in _codigos(a[0])
    assert "DUPLICADO" in _codigos(a[1]) and a[1].status == "BLOQUEIO"
    assert "VALOR_ACIMA_DA_TABELA" in _codigos(a[3]) and a[3].valor_faturavel == 60
    assert "VALOR_ABAIXO_DA_TABELA" in _codigos(a[4]) and a[4].valor_faturavel == 250
    assert "ATO_NAO_REMUNERADO" in _codigos(a[5])
    assert "FORA_DA_COMPETENCIA" in _codigos(a[6])
    assert "ATO_NAO_RECONHECIDO" in _codigos(a[7])
    assert "COLUNA_PRESUMIDA" in _codigos(a[8]) and a[8].coluna == "demais"
    rs = resumo(a)
    assert rs["por_uf"]["AM"]["linhas"] == 9


def test_coluna_divergente_nao_presume_a_maior() -> None:
    a = auditar(
        [_l(acao="Ação de Obrigação de Fazer", ato_texto="Contestação ou defesa", valor=104.0)],
        "2026-07",
    )[0]
    assert "COLUNA_DIVERGENTE" in _codigos(a)
    assert a.valor_faturavel == 104.0


def test_ficha_trocada_sugere_a_correta() -> None:
    benner = {
        "CIVE.1/2015": FichaBenner("CIVE.1/2015", CNJ_B, "Em andamento"),
        "CIVE.2/2015": FichaBenner("CIVE.2/2015", CNJ_A, "Em andamento"),
    }
    a = auditar([_l(ficha="CIVE.1/2015", cnj=CNJ_A)], "2026-07", benner)[0]
    assert "FICHA_TROCADA" in _codigos(a)
    assert a.ficha_sugerida == "CIVE.2/2015"


def test_le_planilha_ignora_total_e_gera_anexo_ii(tmp_path: Path) -> None:
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
            CNJ_A,
            "Itacoatiara",
            "Amazonas",
            "Execução",
            "X",
            "Atos BASA - Petições interlocutórias",
            "2026-07-06 14:14:08",
            120,
        ]
    )
    ws.append(
        [
            "CIVE.3/2020",
            "0801603-50.2026.8.14.0050",
            "Belém",
            "Pará",
            "Execução",
            "Y",
            "Petições de juntada de planilha atualizada de débito",
            "15/07/2026",
            60,
        ]
    )
    ws.append([None, None, None, None, None, None, None, None, 180])  # linha de total
    entrada = tmp_path / "atos.xlsx"
    wb.save(entrada)

    linhas = ler_atos(entrada)
    assert len(linhas) == 2 and linhas[0].data == date(2026, 7, 6)
    saida = tmp_path / "out.xlsx"
    rs = gerar_excel(auditar(linhas, "2026-07"), "2026-07", saida)
    assert set(rs["por_uf"]) == {"AM", "PA"}
    wb2 = load_workbook(saida)
    assert {"Resumo", "Pré-auditoria", "Anexo II - AM", "Anexo II - PA"} <= set(wb2.sheetnames)
    pa = wb2["Anexo II - PA"]
    assert pa.cell(row=2, column=7).value.startswith("Petições de juntada")
    assert pa.cell(row=pa.max_row, column=9).value == 60


def test_uf_por_nome_do_estado() -> None:
    a = auditar(
        [
            _l(uf="Mato Grosso do Sul"),
            _l(uf="Pará", cnj=CNJ_B),
            _l(uf="Rio Grande do Norte", cnj="0000001-77.2017.8.04.3501"),
        ],
        "2026-07",
    )
    assert [x.linha.uf for x in a] == ["MS", "PA", "RN"]
