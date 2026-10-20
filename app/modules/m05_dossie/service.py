"""M5 Dossiê — documento consolidado (fatos, timeline, provas com score, exposição).

Fluxo: (1) páginas dos autos recebem apelidos curtos `P1…Pn` (o modelo cita apelidos, nunca
UUIDs); (2) o LLM extrai, com saída estruturada, os campos de origem `extracao` do playbook
e fatos/timeline/provas ancorados em páginas; (3) o código mescla campos de subsídio (M3),
antifraude (M4) e calculados; (4) as condições das teses e exceções do playbook são avaliadas
deterministicamente. Nada aqui rotula pessoas: flags de fraude entram só como indícios.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.modules.m00_playbook.conditions import all_conditions_met, match_thesis
from app.modules.m00_playbook.schema import Playbook

DOSSIER_PROMPT_VERSION = "dossie-v2"
MAX_CHARS_PER_PAGE = 6000


class Fact(BaseModel):
    text: str
    page_refs: list[str] = Field(default_factory=list, description="apelidos P1, P2…")


class Evidence(BaseModel):
    description: str
    page_refs: list[str] = Field(default_factory=list)
    score: float = Field(ge=0, le=1, description="força probatória para a defesa")
    favors: str = Field(default="defesa", description="defesa | autor | neutro")


class TimelineEvent(BaseModel):
    date: str = Field(description="AAAA-MM-DD ou AAAA-MM quando só o mês é conhecido")
    event: str
    page_refs: list[str] = Field(default_factory=list)


class DossierExtraction(BaseModel):
    """Saída estruturada do LLM (structured output)."""

    fields: dict[str, Any] = Field(
        default_factory=dict,
        description="campos de origem 'extracao' do playbook; omita o que não consta dos autos",
    )
    field_page_refs: dict[str, list[str]] = Field(
        default_factory=dict, description="campo → apelidos das páginas que o sustentam"
    )
    facts: list[Fact]
    timeline: list[TimelineEvent]
    evidences: list[Evidence]
    claims: list[str] = Field(description="pedidos do autor, literalmente resumidos")
    weaknesses: list[str] = Field(description="pontos fracos da defesa à luz dos autos")
    exposure_estimate: float | None = Field(
        default=None, description="exposição máxima em BRL (soma dos pedidos quantificáveis)"
    )
    exposure_basis: str | None = None
    open_questions: list[str] = Field(default_factory=list)


# compat: nome antigo usado por testes/clientes
DossierContent = DossierExtraction


def system_prompt() -> str:
    return (
        "Você é analista jurídico de um escritório que defende instituição financeira em ações "
        "de consignado/RMC não reconhecido no TJPA. Consolide os autos em um dossiê estruturado, "
        "em português, para revisão por advogado. Regras: (1) toda afirmação de fato e toda prova "
        "cita os apelidos de página (P1, P2…) que a sustentam; sem página, não afirme; "
        "(2) preencha só os campos listados cuja resposta consta dos autos, nos tipos pedidos "
        "(datas AAAA-MM-DD, valores em número, booleanos true/false); (3) não classifique pessoas "
        "nem use termos como 'fraudador' ou 'litigante de má-fé' — aponte apenas indícios com a "
        "fonte; (4) não invente dispositivos legais, súmulas ou precedentes; (5) distinga o que "
        "o autor alega do que está provado. Responda apenas com o JSON pedido."
    )


def build_page_index(pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """`pages` = [{document_page_id, document_id, filename, page_number, page_type, text}]."""
    index: dict[str, dict[str, Any]] = {}
    # ordem de upload (documento) e de página — a inicial costuma vir primeiro
    for i, p in enumerate(pages, start=1):
        index[f"P{i}"] = {
            "document_page_id": str(p["document_page_id"]),
            "document_id": str(p["document_id"]),
            "filename": p["filename"],
            "page_number": p["page_number"],
            "page_type": p.get("page_type"),
        }
    return index


def render_pages(pages: list[dict[str, Any]], index: dict[str, dict[str, Any]]) -> str:
    by_id = {str(p["document_page_id"]): p for p in pages}
    blocks = []
    for alias, meta in index.items():
        p = by_id[meta["document_page_id"]]
        text = (p.get("text") or "").strip()[:MAX_CHARS_PER_PAGE]
        blocks.append(
            f"[{alias}] {meta['filename']} — página {meta['page_number']} "
            f"(tipo: {meta.get('page_type') or 'outro'})\n{text or '(sem texto)'}"
        )
    return "\n\n".join(blocks)


def extraction_fields_spec(pb: Playbook | None) -> list[dict[str, str]]:
    if pb is None:
        return []
    return [
        {"campo": c.campo, "tipo": c.tipo.value, "descricao": c.descricao}
        for c in pb.campos_dossie_obrigatorios
        if c.origem.value == "extracao"
    ]


def user_prompt(
    *,
    case_summary: dict[str, Any],
    subsidies: dict[str, Any],
    fraud_flags: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    index: dict[str, dict[str, Any]],
    pb: Playbook | None,
) -> str:
    parts = [
        "## Processo",
        json.dumps(case_summary, ensure_ascii=False, default=str),
        "",
        "## Campos a extrair dos autos (origem: extracao)",
        json.dumps(extraction_fields_spec(pb), ensure_ascii=False),
        "",
        "## Subsídios já informados pelo cliente (não re-extraia; use para apontar contradições)",
        json.dumps(subsidies, ensure_ascii=False, default=str),
        "",
        "## Indícios do antifraude (flags determinísticos, sem decisão humana)",
        json.dumps(fraud_flags, ensure_ascii=False, default=str),
        "",
        "## Autos e subsídios, página a página",
        render_pages(pages, index),
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Mescla de campos e avaliação do playbook (determinístico)
# ---------------------------------------------------------------------------


def antifraud_fields(checks: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for c in checks:
        ev = c.get("evidence") or {}
        code = c.get("check_code")
        if code == "litispendencia":
            out["litispendencia_cnj"] = list(ev.get("cnj") or [])
        elif code == "concentracao_autor" and ev.get("cases") is not None:
            out["acoes_mesmo_autor_mesmo_reu_n"] = int(ev["cases"])
        elif code == "concentracao_advogado_mes" and ev.get("cases") is not None:
            out["acoes_mesmo_advogado_mes_n"] = int(ev["cases"])
        elif code == "autor_falecido":
            out["autor_falecido"] = c.get("result") == "flag"
    return out


def calculated_fields(f: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if f.get("data_primeiro_desconto") and not f.get("data_ciencia_inequivoca"):
        out["data_ciencia_inequivoca"] = f["data_primeiro_desconto"]
    indicio = (
        f.get("geolocalizacao_compativel") is False
        or f.get("conta_credito_titularidade") in {"terceiro", "desconhecida"}
        or (
            f.get("contrato_assinatura_tipo") == "biometria_facial"
            and f.get("documento_selfie_coincide") is False
        )
        or (f.get("ip_log_disponivel") is False and f.get("ted_comprovante_localizado") is False)
    )
    out["indicio_fraude_contra_autor"] = bool(indicio)
    produto = f.get("tipo_produto")
    assinatura_ok = f.get("contrato_assinatura_tipo") in {
        "biometria_facial",
        "assinatura_digital_icp",
        "assinatura_eletronica_simples",
        "digital_telefone",
        "fisica",
    }
    if (
        f.get("contrato_localizado") is True
        and f.get("valor_creditado_conta_autor") is True
        and f.get("conta_credito_titularidade", "autor") == "autor"
        and assinatura_ok
        and not indicio
    ):
        out["hipotese_afastamento_dano_moral"] = "contratacao_provada"
    elif produto in {"rmc", "rcc", "cartao_beneficio"} and f.get("valor_creditado_conta_autor"):
        out["hipotese_afastamento_dano_moral"] = "rmc_credito_recebido"
    elif (f.get("descontos_parcelas_n") or 0) >= 24 and not f.get(
        "reclamacao_administrativa_previa"
    ):
        out["hipotese_afastamento_dano_moral"] = "inercia_prolongada"
    else:
        out["hipotese_afastamento_dano_moral"] = "nenhuma"
    return out


def merge_fields(
    *,
    extracted: dict[str, Any],
    subsidies: dict[str, Any],
    fraud_checks: list[dict[str, Any]],
    case_fields: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Precedência: subsídio do cliente > extração > caso; antifraude e calculados por cima."""
    fields: dict[str, Any] = {}
    sources: dict[str, str] = {}
    for k, v in case_fields.items():
        if v is not None:
            fields[k], sources[k] = v, "caso"
    for k, v in extracted.items():
        if v is not None and v != "":
            fields[k], sources[k] = v, "extracao"
    for k, v in subsidies.items():
        if k.startswith("_") or v is None:
            continue
        fields[k], sources[k] = v, "subsidio"
    for k, v in antifraud_fields(fraud_checks).items():
        fields[k], sources[k] = v, "antifraude"
    for k, v in calculated_fields(fields).items():
        fields[k], sources[k] = v, "calculado"
    return fields, sources


def evaluate_playbook(pb: Playbook | None, fields: dict[str, Any]) -> dict[str, Any]:
    if pb is None:
        return {"applicable_theses": [], "theses_not_applicable": [], "exceptions_triggered": []}
    applicable, not_applicable = [], []
    for t in pb.teses:
        if not t.ativa:
            continue
        conds = [c.model_dump(mode="json") for c in t.condicoes_aplicacao]
        m = match_thesis(t.id, conds, fields)
        if m.applicable:
            applicable.append({"code": t.id, "nome": t.nome, "categoria": t.categoria.value})
        else:
            not_applicable.append({"code": t.id, "unmet": m.unmet})
    exceptions = [
        {
            "id": x.id,
            "acao": x.acao.value,
            "acoes_paralelas": [a.value for a in x.acoes_paralelas],
            "descricao": x.descricao,
        }
        for x in pb.excecoes
        if all_conditions_met([c.model_dump(mode="json") for c in x.condicoes], fields)
    ]
    missing_blocking = [
        c.campo
        for c in pb.campos_dossie_obrigatorios
        if c.bloqueia_minuta_se_ausente and fields.get(c.campo) is None
    ]
    return {
        "applicable_theses": applicable,
        "theses_not_applicable": not_applicable,
        "exceptions_triggered": exceptions,
        "missing_blocking_fields": missing_blocking,
    }


def resolve_refs(refs: list[str], index: dict[str, dict[str, Any]]) -> list[str]:
    return [index[r]["document_page_id"] for r in refs if r in index]


__all__ = [
    "DOSSIER_PROMPT_VERSION",
    "DossierContent",
    "DossierExtraction",
    "Evidence",
    "Fact",
    "TimelineEvent",
    "antifraud_fields",
    "build_page_index",
    "calculated_fields",
    "evaluate_playbook",
    "merge_fields",
    "render_pages",
    "resolve_refs",
    "system_prompt",
    "user_prompt",
]
