"""Motor de oportunidades — movimentos TPU → eventos → atos, e conciliação com o cobrado."""

from __future__ import annotations

from datetime import date

from app.modules.m12_faturamento.deteccao import (
    Processo,
    conciliar,
    detectar,
    eventos_do_movimento,
    polo_do_banco,
)

CNJ = "08032139620208140039"


def _m(cod: int, nome: str, data: str, *comps: str) -> dict[str, object]:
    return {
        "codigo": cod,
        "nome": nome,
        "dataHora": f"{data}T10:00:00.000Z",
        "complementosTabelados": [{"nome": c} for c in comps],
    }


def test_polo_pela_classe() -> None:
    assert polo_do_banco("Execução de Título Extrajudicial") == "autor"
    assert polo_do_banco("Embargos à Execução") == "embargado"
    assert polo_do_banco("Procedimento Comum Cível") == "reu"


def test_sentenca_depende_do_polo() -> None:
    improc = _m(220, "Improcedência", "2026-07-10")
    assert [e.nome for e in eventos_do_movimento(improc, "autor")] == ["sentenca_desfavoravel"]
    assert [e.nome for e in eventos_do_movimento(improc, "reu")] == ["sentenca_favoravel"]
    proc = _m(219, "Procedência", "2026-07-10")
    assert [e.nome for e in eventos_do_movimento(proc, "embargado")] == ["sentenca_desfavoravel"]


def test_mandado_audiencia_e_extincao() -> None:
    neg = _m(106, "Mandado", "2026-07-01", "não entregue ao destinatário")
    assert eventos_do_movimento(neg, "autor")[0].nome == "citacao_negativa"
    aud = _m(12740, "de Conciliação", "2026-07-02", "Conciliador(a)", "realizada")
    assert [e.nome for e in eventos_do_movimento(aud, "autor")] == [
        "audiencia_conciliacao_realizada"
    ]
    ext = _m(466, "Homologação de Transação", "2026-07-03")
    assert eventos_do_movimento(ext, "autor")[0].nome == "sentenca_extincao_acordo"


def test_detectar_e_conciliar() -> None:
    p = Processo(
        CNJ,
        "Execução de Título Extrajudicial",
        "TJPA",
        [
            _m(220, "Improcedência", "2026-07-10"),
            _m(1049, "Pagamento integral do débito", "2026-08-01"),
            _m(12740, "de Conciliação", "2026-08-05", "Conciliador(a)", "realizada"),
        ],
    )
    p.ultima_movimentacao = date(2026, 8, 5)
    ops = detectar(p, hoje=date(2026, 11, 10))
    por = {o.evento: o for o in ops}
    assert por["sentenca_desfavoravel"].ato_id == "apelacao"
    assert por["sentenca_desfavoravel"].valor == 250
    assert por["sentenca_extincao_pagamento"].valor == 110
    assert "processo_sem_evento_90_dias" in por
    cobrados = {CNJ: [(date(2026, 7, 25), "apelacao")]}
    conciliar(ops, cobrados, hoje=date(2026, 11, 10))
    assert por["sentenca_desfavoravel"].status == "ATENDIDA"
    assert por["sentenca_extincao_pagamento"].status == "PERDIDA"
    assert por["audiencia_conciliacao_realizada"].status == "PERDIDA"
