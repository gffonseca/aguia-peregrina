"""M0 Playbook: o template e o playbook de consignado/RMC validam; a regra 'aprovado só com OAB,
timestamp e referências conferidas' é invariante; o JSON Schema publicado está em dia."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest
import yaml

from app.modules.m00_playbook.schema import (
    Playbook,
    PlaybookValidationError,
    export_json_schema,
    to_thesis_payloads,
    validate_playbook,
)

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS = ROOT / "playbooks"
TEMPLATE = PLAYBOOKS / "TEMPLATE.playbook.yaml"
CONSIGNADO = PLAYBOOKS / "consignado-rmc-tjpa.playbook.yaml"
EXECUCAO_BASA = PLAYBOOKS / "execucao-credito-basa-tjpa-tjam.playbook.yaml"


@pytest.mark.parametrize("path", sorted(PLAYBOOKS.glob("*.playbook.yaml")), ids=lambda p: p.name)
def test_every_playbook_file_validates(path: Path) -> None:
    pb = validate_playbook(path)
    assert pb.schema_version == "1.0"
    assert pb.metadata.autor_oab


def test_consignado_content_matches_spec() -> None:
    pb = validate_playbook(CONSIGNADO)
    assert pb.metadata.tipologia == "consignado_rmc_nao_reconhecido"
    assert pb.metadata.tribunal == "TJPA"
    assert pb.metadata.lado == "defesa"
    assert pb.metadata.status == "aprovado"
    assert pb.metadata.aprovado_por_oab == "PA 12724"
    assert pb.metadata.aprovado_em is not None
    nomes = " ".join(t.nome.lower() for t in pb.teses)
    for termo in (
        "biometria",
        "recebimento",
        "dano moral",
        "litispendência",
        "fracionamento",
        "prescrição",
        "compensação",
        "gratuidade",
        "1.198",
        "predatória",
    ):
        assert termo in nomes, termo
    codigos = {c.codigo for c in pb.antifraude.checagens}
    assert {
        "comprovante_endereco_terceiro",
        "concentracao_advogado_mes",
        "autor_falecido",
        "procuracao_antiga",
    } <= codigos
    # Sessão 2 (20/10/2026): toda referência legal conferida, com fonte na nota; nenhum
    # placeholder sobrou nas refs nem nos assuntos CNJ.
    assert pb.referencias_nao_conferidas() == []
    for t in pb.teses:
        for r in (*t.fundamentacao.dispositivos, *t.fundamentacao.precedentes):
            assert r.conferido and "A CONFERIR" not in r.nota and "Conferido" in r.nota, (
                t.id,
                r.ref,
            )
    assert all(a.conferido for a in pb.gatilhos_classificacao.assuntos_cnj)
    # Subtese aponta para a mãe e a árvore é navegável.
    assert pb.tese("T06.1").pai == "T06"
    assert pb.tese("T06.1.1").pai == "T06.1"
    assert pb.tese("T08.1").pai == "T08"
    assert pb.criterios_revisao.tempo_minimo_segundos >= 900


def test_consignado_encodes_review_session_1_decisions() -> None:
    """Decisões da sessão de revisão de 2026-10-19 (conteúdo preservado após a aprovação v1)."""
    pb = validate_playbook(CONSIGNADO)
    assert pb.metadata.status == "aprovado"
    assert pb.metadata.versao == 1
    assert [r.data.isoformat() for r in pb.metadata.revisoes][0] == "2026-10-19"
    assert "12.724" in pb.metadata.revisoes[0].por
    assert pb.metadata.piloto is not None and pb.metadata.piloto.cliente_piloto is None

    # 2 e 4: as pendências de levantamento TJPA em T05 e T06.1 foram fechadas na sessão 2
    assert pb.tese("T05").pendencia is None
    assert pb.tese("T06.1").pendencia is None
    assert pb.tese("T06.1").pai == "T06"  # 1: RMC segue como subtese

    # 5: escalada em três níveis; (b) e (c) exigem dupla autorização registrada
    niveis = {n.nivel: n for n in pb.tese("T10").providencias_escalonadas}
    assert set(niveis) == {"a", "b", "c"}
    assert not niveis["a"].autorizacao_dupla
    assert niveis["b"].autorizacao_dupla and niveis["c"].autorizacao_dupla
    dupla = pb.criterios_revisao.autorizacao_dupla
    assert dupla is not None
    assert {"sócio FBS", "jurídico do cliente"} <= set(dupla.autorizadores)
    assert "plataforma" in dupla.registro.lower()

    # 7, 8, 9, 13: exceções
    x = {e.id: e for e in pb.excecoes}
    assert x["X01"].acao == "pedir_subsidio"
    assert {"sinalizar_acordo", "gerar_minuta_sem_merito", "escalar_advogado_carteira"} <= {
        a.value for a in x["X01"].acoes_paralelas
    }
    assert x["X03"].acao == "sinalizar_acordo"
    assert x["X05"].condicoes[0].valor == 30000.0
    assert x["X08"].acao == "alertar_revisor"
    assert not any(
        c.campo == "valor_contrato" for r in pb.sinais_acordo.quando_acordar for c in r.condicoes
    )

    # 10 e 12: sem alçadas por valor; recomendação FBS → aprovação do cliente; faixas provisórias
    assert pb.sinais_acordo.alcadas == []
    assert pb.sinais_acordo.fluxo_aprovacao is not None
    assert all(f.provisorio and f.recalibrar_em_dias == 90 for f in pb.sinais_acordo.faixas_valor)

    # 11: concentração de advogado em dois níveis; procuração antiga 180 dias; revisão 15 min
    conc = next(c for c in pb.antifraude.checagens if c.codigo == "concentracao_advogado_mes")
    assert conc.parametros["niveis"] == {"atencao": 10, "forte": 30}
    antiga = next(c for c in pb.antifraude.checagens if c.codigo == "procuracao_antiga")
    assert antiga.parametros["max_dias"] == 180
    assert pb.criterios_revisao.tempo_minimo_segundos == 900
    assert any(
        c.campo == "valor_causa" and c.valor == 30000.0
        for c in pb.criterios_revisao.exige_segunda_revisao_se
    )

    # 14: disponibilidade a confirmar com o cliente
    campos = {c.campo: c for c in pb.campos_dossie_obrigatorios}
    for campo in ("ip_log_disponivel", "biometria_score", "valor_creditado_conta_autor"):
        assert campos[campo].disponibilidade == "a confirmar com cliente"


def test_consignado_encodes_review_session_2_decisions() -> None:
    """Decisões da sessão 2 (2026-10-20): referências conferidas contra o levantamento;
    T01/T05/T06.1/T08/T09 ajustados. Aprovado v1 em 20/10/2026 (Gustavo Fonseca, OAB/PA 12.724)."""
    pb = validate_playbook(CONSIGNADO)
    assert pb.metadata.status == "aprovado"
    assert pb.metadata.aprovado_por_oab == "PA 12724"
    assert pb.metadata.aprovado_em is not None
    assert pb.metadata.autor_nome == "Gustavo Fonseca"
    assert pb.metadata.autor_oab == "PA 12724"
    assert [r.data.isoformat() for r in pb.metadata.revisoes] == ["2026-10-19", "2026-10-20"]
    assert "Sessão 2" in pb.metadata.revisoes[1].resumo

    # 1: T05 — CDC 27, trato sucessivo, sem pendência; CC 205/206 só como afastados
    t05 = pb.tese("T05")
    assert t05.pendencia is None
    refs05 = " ".join(r.ref for r in t05.fundamentacao.dispositivos)
    assert "CDC, art. 27" in refs05
    assert any("AFASTADOS" in r.para_que_serve for r in t05.fundamentacao.dispositivos)
    prec05 = " ".join(r.ref for r in t05.fundamentacao.precedentes)
    for n in ("1.056.534", "1.728.230", "0004156-73.2019.8.14.0107", "0805230-14.2024.8.14.0024"):
        assert n in prec05, n

    # 2: T06.1 condicional (TCE) + T06.1.1 subsidiária + X09 sinaliza acordo
    t061 = pb.tese("T06.1")
    assert t061.pendencia is None
    assert any(
        c.campo == "rmc_tce_localizado" and c.valor is True for c in t061.condicoes_aplicacao
    )
    t0611 = pb.tese("T06.1.1")
    assert t0611.categoria == "subsidiaria"
    assert any(
        c.campo == "rmc_tce_localizado" and c.valor is False for c in t0611.condicoes_aplicacao
    )
    x = {e.id: e for e in pb.excecoes}
    assert x["X09"].acao == "sinalizar_acordo"
    assert "0800613-16.2024.8.14.0087" in " ".join(r.ref for r in t0611.fundamentacao.precedentes)

    # 3: T08 só nas três hipóteses; T08.1 quantum + Tema 1.435
    t08 = pb.tese("T08")
    hip = next(c for c in t08.condicoes_aplicacao if c.campo == "hipotese_afastamento_dano_moral")
    assert set(hip.valor) == {"contratacao_provada", "inercia_prolongada", "rmc_credito_recebido"}
    t081 = pb.tese("T08.1")
    assert any("1.435" in r.ref and "2.219.864" in r.ref for r in t081.fundamentacao.precedentes)
    assert "R$ 3.000" in t081.nome

    # 4: Tema 1.198 = emenda por litigância abusiva, com datas
    t02 = pb.tese("T02")
    tema = next(r for r in t02.fundamentacao.precedentes if "1.198" in r.ref)
    assert "13/03/2025" in tema.ref and "11/06/2026" in tema.ref and tema.conferido

    # 5: T09 — EAREsp com datas corretas; pendência do Tema 929
    t09 = pb.tese("T09")
    eare = next(r for r in t09.fundamentacao.precedentes if "676.608" in r.ref)
    assert "21/10/2020" in eare.ref and "30/03/2021" in eare.ref
    assert "Tema 929" in (t09.pendencia or "") and "M9" in (t09.pendencia or "")

    # 6: T01 sem critério objetivo na peça; AI 0820042-02.2025.8.14.0000
    t01 = pb.tese("T01")
    assert any("0820042-02.2025.8.14.0000" in r.ref for r in t01.fundamentacao.precedentes)
    assert not any("3 salários" in a or "3 SM" in a for a in t01.fundamentacao.argumentos_chave)

    # 7 e 8: Lei 10.820 (45%, IN 138/2022 → 213/2026); REsp 2.197.156/SP; sem Lei 14.509
    t06 = pb.tese("T06")
    refs06 = " ".join(
        r.ref for r in (*t06.fundamentacao.dispositivos, *t06.fundamentacao.precedentes)
    )
    assert "45%" in refs06 and "213" in refs06 and "2.197.156" in refs06 and "1.846.649" in refs06
    assert "14.509" not in refs06
    codigos = {a.codigo for a in pb.gatilhos_classificacao.assuntos_cnj}
    assert {"11806", "9607", "9585", "7772", "10433", "11811"} <= codigos

    # 9: nenhuma menção à "Recomendação CFOAB 001/2024"
    texto = CONSIGNADO.read_text(encoding="utf-8")
    assert "CFOAB" not in texto
    assert "[A CONFERIR" not in texto

    # 10: T04/T10 — emenda proporcional; nunca cópia do contrato; escalada mantida
    for tid in ("T04", "T10"):
        t = pb.tese(tid)
        assert "cópia do contrato" in t.resumo.lower() or any(
            "cópia do contrato" in n.descricao.lower() for n in t.providencias_escalonadas
        )
        assert {n.nivel for n in t.providencias_escalonadas} == {"a", "b", "c"}

    # 11: faixas seguem provisórias e não bloqueiam a aprovação
    assert all(f.provisorio for f in pb.sinais_acordo.faixas_valor)
    assert "R$ 3.000–5.000" in (pb.sinais_acordo.nota_calibracao or "")


def test_consignado_would_pass_approval_invariant() -> None:
    """Dry-run: com OAB + timestamp, o playbook passa na invariante de aprovação (não altera
    o arquivo — a aprovação é decisão registrada pelo advogado-dono)."""
    raw = _raw(CONSIGNADO)
    raw["metadata"]["status"] = "aprovado"
    raw["metadata"]["aprovado_por_oab"] = "PA 12724"
    raw["metadata"]["aprovado_por_nome"] = "Gustavo Fonseca"
    raw["metadata"]["aprovado_em"] = "2026-10-20T12:00:00-03:00"
    pb = Playbook.model_validate(raw)
    assert pb.metadata.status == "aprovado"


def test_polo_defaults_to_passivo_and_accepts_ativo() -> None:
    """`metadata.polo` entrou com a tipologia de execução de crédito (credor = BASA)."""
    raw = _raw(TEMPLATE)
    raw["metadata"].pop("polo", None)
    assert Playbook.model_validate(copy.deepcopy(raw)).metadata.polo == "passivo"
    raw["metadata"]["polo"] = "ativo"
    assert Playbook.model_validate(copy.deepcopy(raw)).metadata.polo == "ativo"
    raw["metadata"]["polo"] = "terceiro"
    with pytest.raises(ValueError, match="polo"):
        Playbook.model_validate(raw)


def test_execucao_basa_is_polo_ativo_draft() -> None:
    pb = validate_playbook(EXECUCAO_BASA)
    assert pb.metadata.polo == "ativo"
    assert pb.metadata.lado == "autor"
    assert pb.metadata.status == "em_revisao"
    assert pb.metadata.aprovado_em is None
    assert pb.metadata.tribunal == "TJPA"
    assert pb.metadata.autor_oab == "PA 12724"
    assert pb.metadata.piloto is not None and "BASA" in (pb.metadata.piloto.cliente_piloto or "")
    nomes = " ".join(t.nome.lower() for t in pb.teses)
    for termo in (
        "recuperabilidade",
        "impulso",
        "embargos",
        "pré-executividade",
        "921",
        "monitória",
    ):
        assert termo in nomes, termo
    # Rascunho: nada conferido ainda.
    assert pb.referencias_nao_conferidas()
    assert all(not a.conferido for a in pb.gatilhos_classificacao.assuntos_cnj)
    assert pb.sinais_acordo.fluxo_aprovacao is not None
    # Peça de impulso é curta: tempo mínimo menor que o da contestação (900 s).
    assert 60 <= pb.criterios_revisao.tempo_minimo_segundos < 900


def test_execucao_basa_encodes_review_session_1_decisions() -> None:
    """Decisões da sessão 1 (2026-10-20) do playbook de execução BASA: triagem, impulso
    cumulado, embargos, acordo proativo, monitoramento 90 d, intercorrente, amostra top-200.
    Referências legais seguem todas `conferido: false` (não validadas ainda)."""
    pb = validate_playbook(EXECUCAO_BASA)
    assert pb.metadata.status == "em_revisao"
    assert [r.data.isoformat() for r in pb.metadata.revisoes] == ["2026-10-20"]
    assert "12.724" in pb.metadata.revisoes[0].por and "Sessão 1" in pb.metadata.revisoes[0].resumo
    assert pb.referencias_nao_conferidas()
    assert all(not a.conferido for a in pb.gatilhos_classificacao.assuntos_cnj)
    campos = {c.campo: c for c in pb.campos_dossie_obrigatorios}
    texto = EXECUCAO_BASA.read_text(encoding="utf-8")

    # 1 e 3: carteira morta = três critérios; intercorrente fora; decisão de sócio caso a caso
    t011 = pb.tese("T01.1")
    assert t011.pai == "T01"
    for termo in ("Sisbajud + Renajud + Infojud", "3 anos", "falecido", "custo"):
        assert termo in t011.resumo, termo
    assert "sem_bens_e_3_anos_parado" in campos["carteira_morta_criterios"].descricao
    assert "falecido_sem_herdeiros" in campos["carteira_morta_criterios"].descricao
    assert "valor_abaixo_custo" in campos["carteira_morta_criterios"].descricao
    assert "NÃO" in campos["carteira_morta_criterios"].descricao  # intercorrente não entra
    assert "morta_cessao" not in texto and "morta_baixa" not in texto
    assert "socio_decisao_carteira_morta" in campos
    x = {e.id: e for e in pb.excecoes}
    assert x["X03"].acao == "escalar_socio"
    assert "lote" in (x["X03"].nota or "")
    seg = {c.campo: c for c in pb.criterios_revisao.exige_segunda_revisao_se}
    assert seg["recomendacao_triagem"].valor == "morta"
    assert "SÓCIO" in (seg["recomendacao_triagem"].nota or "")
    assert any(
        "lote" in s and "sócio" in s for s in pb.criterios_revisao.exige_segunda_revisao_tambem
    )

    # 2: piso de R$ 10.000 provisório, a definir com o BASA
    piso = next(c for c in pb.antifraude.checagens if c.codigo == "valor_abaixo_piso_diligencia")
    assert piso.parametros["piso_brl"] == 10000 and piso.parametros["provisorio"] is True
    assert "definir com o BASA" in piso.parametros["nota"]

    # 4: cessão fora do playbook — só a nota neutra em observacoes
    assert (
        "cessão de crédito não é objeto deste playbook" in (pb.metadata.observacoes or "").lower()
    )
    for t in pb.teses:
        corpo = " ".join([t.nome, t.resumo, *t.pedidos, *t.fundamentacao.argumentos_chave])
        assert not re.search(r"\bcess[ãa]o\b", corpo.lower()), t.id  # 'sucessão' não conta
    assert "spinoff" not in texto.lower() and "altavista" not in texto.lower()

    # 5: pisos de revisão 300 / 600 / 1200 e lote diário
    assert pb.criterios_revisao.tempo_minimo_segundos == 300
    assert "lote" in (pb.criterios_revisao.observacoes or "").lower()
    assert "1.200 s" in (pb.criterios_revisao.observacoes or "")

    # 6: pedido cumulado + fallback sequencial aprendido por juízo
    t022 = pb.tese("T02.2")
    assert "CUMULADO" in t022.nome and "sequencial" in t022.nome
    assert "preferencia_juizo_cumulado" in campos
    assert any(c.campo == "preferencia_juizo_cumulado" for c in t022.condicoes_aplicacao)
    assert (
        "requerimento_cumulado_sisbajud_renajud_infojud" in campos["tipo_peca_prevista"].descricao
    )
    assert "CNIB" in pb.tese("T02.3").nome

    # 7: excesso de execução — planilha sempre; rejeição liminar; recálculo pelo portal BASA
    t061 = pb.tese("T06.1")
    assert "SEMPRE" in t061.nome and "917" in t061.nome
    assert "rejeição liminar" in t061.pedidos[0].lower()
    assert "portal BASA" in t061.resumo

    # 8: acordo proativo em score médio com bens parciais; fluxo FBS → BASA → registro
    t091 = pb.tese("T09.1")
    assert t091.pai == "T09" and t091.categoria == "sinal"
    assert {c.campo for c in t091.condicoes_aplicacao} >= {
        "recomendacao_triagem",
        "bens_cobertura_pct",
    }
    assert pb.sinais_acordo.fluxo_aprovacao is not None
    assert "fbs_proativa" in campos["acordo_iniciativa"].descricao

    # 9: 90 dias sem movimentação útil → alerta + impulso automático (provisório, SLA BASA)
    parado = next(c for c in pb.antifraude.checagens if c.codigo == "processo_parado_90_dias")
    assert parado.parametros["dias"] == 90 and parado.parametros["provisorio"] is True
    assert "SLA do contrato BASA" in parado.parametros["nota"]
    assert x["X12"].acao == "alertar_revisor"
    assert any(
        c.campo == "dias_sem_andamento" and c.valor == 90 and "provisorio" in (c.nota or "")
        for c in x["X12"].condicoes
    )

    # 10: prescrição intercorrente por processo; < 12 meses; diligência útil obrigatória
    t081 = pb.tese("T08.1")
    assert t081.pai == "T08"
    assert any(
        c.campo == "prescricao_intercorrente_meses_restantes" and c.valor == 12
        for c in t081.condicoes_aplicacao
    )
    assert "prescricao_intercorrente_data_limite" in campos
    assert any(
        i.id == "R11" and i.bloqueante and "12 meses" in i.item
        for i in pb.criterios_revisao.checklist
    )
    assert any(m.id == "M13" and "< 12" in m.nome for m in pb.metricas)
    inter = next(
        c for c in pb.antifraude.checagens if c.codigo == "prescricao_intercorrente_proxima"
    )
    assert inter.parametros["alerta_meses_antes"] == 12

    # 11: amostra do piloto = top-200 por valor atualizado com bens localizados
    piloto = pb.metadata.piloto
    assert piloto is not None and piloto.amostra is not None
    for termo in (
        "200",
        "MAIOR valor atualizado",
        "bens localizados",
        "moeda antiga",
        "CNJ válido",
        "fallback",
    ):
        assert termo in piloto.amostra, termo

    # 12: portal BASA — pendência externa (dono Gustavo) e disponibilidade a confirmar
    assert any(
        p.dono == "Gustavo" and "portal" in p.descricao.lower() for p in piloto.pendencias_externas
    )
    assert "portal BASA — a mapear" not in texto
    for campo in ("titulo_tipo", "valor_divida_atualizado", "memoria_calculo_disponivel"):
        assert (
            campos[campo].disponibilidade == "a confirmar — portal BASA (documentação solicitada)"
        )


def test_dual_authorization_block_is_required_when_a_level_demands_it() -> None:
    raw = _raw(CONSIGNADO)
    raw["criterios_revisao"].pop("autorizacao_dupla")
    with pytest.raises(ValueError, match="autorizacao_dupla"):
        Playbook.model_validate(raw)


def test_sinais_acordo_requires_fluxo_or_alcadas() -> None:
    raw = _raw(TEMPLATE)
    raw["sinais_acordo"].pop("fluxo_aprovacao")
    with pytest.raises(ValueError, match="fluxo_aprovacao"):
        Playbook.model_validate(raw)


def _raw(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_approved_requires_oab_timestamp_and_checked_refs() -> None:
    raw = _raw(TEMPLATE)
    raw["metadata"]["status"] = "aprovado"
    with pytest.raises(ValueError, match="aprovado_por_oab"):
        Playbook.model_validate(copy.deepcopy(raw))

    raw["metadata"]["aprovado_por_oab"] = "PA 12724"
    raw["metadata"]["aprovado_por_nome"] = "Gustavo Fonseca"
    raw["metadata"]["aprovado_em"] = "2026-10-20T10:00:00-03:00"
    with pytest.raises(ValueError, match="não conferidas"):
        Playbook.model_validate(copy.deepcopy(raw))

    for t in raw["teses"]:
        for grupo in ("dispositivos", "precedentes"):
            for r in t["fundamentacao"][grupo]:
                r["conferido"] = True
    for a in raw["gatilhos_classificacao"]["assuntos_cnj"]:
        a["conferido"] = True
    pb = Playbook.model_validate(raw)
    assert pb.metadata.status == "aprovado"
    assert pb.metadata.aprovado_em is not None


def test_cross_references_are_enforced() -> None:
    raw = _raw(TEMPLATE)
    raw["teses"][0]["condicoes_aplicacao"].append(
        {"campo": "campo_inexistente", "operador": "==", "valor": 1}
    )
    with pytest.raises(ValueError, match="campo_inexistente"):
        Playbook.model_validate(raw)

    raw = _raw(TEMPLATE)
    raw["modelo_peca"]["secoes"][2]["teses_vinculadas"] = ["T99"]
    with pytest.raises(ValueError, match="T99"):
        Playbook.model_validate(raw)

    raw = _raw(TEMPLATE)
    raw["teses"][0]["condicoes_aplicacao"][0] = {
        "campo": "valor_causa",
        "operador": "existe",
        "valor": 1,
    }
    with pytest.raises(ValueError, match="não aceita"):
        Playbook.model_validate(raw)


def test_invalid_file_raises_readable_error(tmp_path: Path) -> None:
    bad = tmp_path / "x.playbook.yaml"
    bad.write_text("- apenas: uma lista\n", encoding="utf-8")
    with pytest.raises(PlaybookValidationError, match="mapeamento"):
        validate_playbook(bad)


def test_json_schema_file_is_in_sync() -> None:
    published = json.loads((PLAYBOOKS / "playbook.schema.json").read_text(encoding="utf-8"))
    assert published == export_json_schema(), (
        "playbooks/playbook.schema.json desatualizado — rode: "
        "python -c 'from app.modules.m00_playbook.schema import write_json_schema as w; "
        'w("playbooks/playbook.schema.json")\''
    )


def test_to_thesis_payloads_matches_m0_model() -> None:
    pb = validate_playbook(CONSIGNADO)
    payloads = to_thesis_payloads(pb)
    assert len(payloads) == len(pb.teses)
    first = payloads[0]
    assert set(first) >= {
        "typology",
        "code",
        "title",
        "parent_code",
        "body_markdown",
        "conditions",
        "author_oab",
    }
    assert first["typology"] == pb.metadata.tipologia
    # Consignado já está conferido (sessão 2): nenhum placeholder vai para o corpo da tese.
    assert "[A CONFERIR pelo advogado-dono]" not in first["body_markdown"]
    filho = next(p for p in payloads if p["code"] == "T06.1")
    assert filho["parent_code"] == "T06"
    # Em um rascunho, o placeholder continua sendo propagado para o body_markdown.
    rascunho = to_thesis_payloads(validate_playbook(TEMPLATE))
    assert any("[A CONFERIR pelo advogado-dono]" in p["body_markdown"] for p in rascunho)
