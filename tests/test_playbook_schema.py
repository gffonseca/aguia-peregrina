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
    assert pb.metadata.status == "rascunho"
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
