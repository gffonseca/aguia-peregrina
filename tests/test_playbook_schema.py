"""M0 Playbook: o template e o playbook de consignado/RMC validam; a regra 'aprovado só com OAB,
timestamp e referências conferidas' é invariante; o JSON Schema publicado está em dia."""

from __future__ import annotations

import copy
import json
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
    assert pb.metadata.status == "em_revisao"
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
    # Rascunho: toda referência legal ainda está marcada para conferência.
    assert pb.referencias_nao_conferidas()
    assert all(
        not r.conferido
        for t in pb.teses
        for r in (*t.fundamentacao.dispositivos, *t.fundamentacao.precedentes)
    )
    # Subtese aponta para a mãe e a árvore é navegável.
    assert pb.tese("T06.1").pai == "T06"
    assert pb.criterios_revisao.tempo_minimo_segundos >= 900


def test_consignado_encodes_review_session_1_decisions() -> None:
    """Decisões da sessão de revisão de 2026-10-19 (status segue em_revisao, nada aprovado)."""
    pb = validate_playbook(CONSIGNADO)
    assert pb.metadata.status == "em_revisao"
    assert pb.metadata.aprovado_em is None
    assert pb.metadata.versao == 1
    assert [r.data.isoformat() for r in pb.metadata.revisoes] == ["2026-10-19"]
    assert "12.724" in pb.metadata.revisoes[0].por
    assert pb.metadata.piloto is not None and pb.metadata.piloto.cliente_piloto is None

    # 2 e 4: pendências de levantamento TJPA em T05 e T06.1
    assert "TJPA" in (pb.tese("T05").pendencia or "")
    assert "TJPA" in (pb.tese("T06.1").pendencia or "")
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

    # 16: referências continuam não conferidas
    assert pb.referencias_nao_conferidas()


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
    assert "[A CONFERIR pelo advogado-dono]" in first["body_markdown"]
    filho = next(p for p in payloads if p["code"] == "T06.1")
    assert filho["parent_code"] == "T06"
