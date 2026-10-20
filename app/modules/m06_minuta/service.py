"""M6 Minuta — contestação gerada de M0 (teses aprovadas) + M5 (dossiê), com citações por página.

A peça é SUGESTÃO: sai como `drafts.status=generated` e só é exportável após a revisão (M7).
O modelo cita páginas pelos apelidos `P1…Pn` do dossiê; o código converte para
`draft_citations.document_page_id` e descarta citações para páginas inexistentes.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from app.modules.m00_playbook.schema import Playbook

DRAFT_PROMPT_VERSION = "minuta-v3"
MAX_CHARS_PER_PAGE = 3500
_REF = re.compile(r"\[(P\d+)\]")


class Citation(BaseModel):
    anchor: str = Field(description="trecho curto da minuta (≤ 120 caracteres) que faz a afirmação")
    page_ref: str = Field(description="apelido da página (P1, P2…)")
    quote: str | None = Field(default=None, description="trecho literal da página, se houver")
    evidence_score: float = Field(ge=0, le=1)


class DraftOutput(BaseModel):
    body_markdown: str = Field(
        description="peça completa em Markdown; cada afirmação de fato termina com [Pn]"
    )
    citations: list[Citation]
    confidence: float = Field(ge=0, le=1)
    thesis_codes_used: list[str]
    open_questions: list[str] = Field(default_factory=list)
    reviewer_alerts: list[str] = Field(default_factory=list)


def system_prompt(draft_type: str) -> str:
    return (
        f"Você redige uma {draft_type} cível (TJPA) como SUGESTÃO para revisão obrigatória por "
        "advogado inscrito na OAB. Regras inegociáveis: (1) use apenas as teses aprovadas "
        "fornecidas, com os argumentos e pedidos de cada uma; não acrescente teses; (2) toda "
        "afirmação de fato cita a página dos autos ou do subsídio com o apelido entre colchetes, "
        "ex.: 'o valor foi creditado em conta do autor [P14]'; sem página, não afirme; (3) cite "
        "somente os dispositivos, súmulas, temas e precedentes que aparecem nas teses fornecidas "
        "e marcados como conferidos; nunca invente número de tema, súmula ou acórdão; (4) siga a "
        "ordem e os títulos das seções do modelo de peça; seções sem tese aplicável e não "
        "obrigatórias podem ser omitidas; (5) português formal, frases curtas, sem adjetivar o "
        "autor ou o advogado adverso; tom respeitoso com pessoa idosa/beneficiária do INSS; "
        "(6) nunca qualifique o autor como fraudador ou litigante de má-fé: a peça só pode "
        "descrever indícios documentados; (7) deixe lacunas como «[REVISOR: …]» quando faltar "
        "dado (endereçamento, nome do advogado subscritor, data); (8) extensão-alvo da peça: "
        "entre 12.000 e 18.000 caracteres — objetiva, sem repetir a mesma prova em várias "
        "seções; no máximo 30 citações. Responda apenas com o JSON pedido; o Markdown vai no "
        "campo body_markdown."
    )


def render_theses(theses: list[dict[str, Any]]) -> str:
    blocks = []
    for t in theses:
        blocks.append(
            f"### {t['code']} — {t['title']} (categoria: {t['categoria']}, "
            f"versão {t['version']} aprovada por OAB {t['approved_by_oab']})\n{t['body_markdown']}"
        )
    return "\n\n".join(blocks) or "(nenhuma tese aplicável)"


def render_sections(pb: Playbook | None, applicable_codes: set[str]) -> str:
    if pb is None:
        return "1. Síntese; 2. Preliminares; 3. Mérito; 4. Pedidos; 5. Provas."
    lines = []
    for s in sorted(pb.modelo_peca.secoes, key=lambda s: s.ordem):
        teses = [c for c in s.teses_vinculadas if c in applicable_codes]
        if s.teses_vinculadas and not teses and not s.obrigatoria:
            continue
        lines.append(
            f"{s.ordem}. **{s.titulo}** (id: {s.id}; obrigatória: {s.obrigatoria}; "
            f"teses: {', '.join(teses) or '—'}; exige citação de página: "
            f"{s.exige_citacao_de_pagina})\n   Instruções: {s.instrucoes}"
        )
    estilo = "\n".join(f"- {e}" for e in pb.modelo_peca.estilo)
    return "\n".join(lines) + ("\n\nEstilo:\n" + estilo if estilo else "")


def render_dossier(content: dict[str, Any]) -> str:
    keep = {
        "fields": content.get("fields"),
        "field_sources": content.get("field_sources"),
        "facts": content.get("facts"),
        "timeline": content.get("timeline"),
        "evidences": content.get("evidences"),
        "claims": content.get("claims"),
        "weaknesses": content.get("weaknesses"),
        "open_questions": content.get("open_questions"),
        "fraud_flags": content.get("fraud_flags"),
        "exceptions_triggered": content.get("exceptions_triggered"),
    }
    return json.dumps(keep, ensure_ascii=False, default=str)


def render_pages(pages: list[dict[str, Any]], index: dict[str, dict[str, Any]]) -> str:
    by_id = {str(p["document_page_id"]): p for p in pages}
    out = []
    for alias, meta in index.items():
        p = by_id.get(meta["document_page_id"])
        text = ((p or {}).get("text") or "").strip()[:MAX_CHARS_PER_PAGE]
        out.append(
            f"[{alias}] {meta['filename']} p.{meta['page_number']} "
            f"({meta.get('page_type') or 'outro'})\n{text}"
        )
    return "\n\n".join(out)


def user_prompt(
    *,
    case_summary: dict[str, Any],
    dossier_content: dict[str, Any],
    theses: list[dict[str, Any]],
    pb: Playbook | None,
    pages: list[dict[str, Any]],
    operator_context: str = "",
) -> str:
    codes = {t["code"] for t in theses}
    dossier_pages = dossier_content.get("page_index") or {}
    parts = [
        "## Processo",
        json.dumps(case_summary, ensure_ascii=False, default=str),
        "",
        "## Modelo de peça (seções, em ordem)",
        render_sections(pb, codes),
        "",
        "## Teses aprovadas aplicáveis a este caso (use só estas)",
        render_theses(theses),
        "",
        "## Dossiê (M5) — fatos, campos, provas; document_page_ids já resolvidos",
        render_dossier(dossier_content),
        "",
        "## Páginas disponíveis para citação (apelidos [Pn])",
        render_pages(pages, dossier_pages),
    ]
    if operator_context:
        parts += ["", "## Observações do operador", operator_context]
    return "\n".join(parts)


def humanize_refs(body: str, index: dict[str, dict[str, Any]]) -> str:
    """`[P3]` → `[P3: contrato.pdf, p. 2]` — mantém o apelido (rastreável) e fica legível."""

    def _sub(m: re.Match[str]) -> str:
        meta = index.get(m.group(1))
        if not meta:
            return m.group(0)
        return f"[{m.group(1)}: {meta['filename']}, p. {meta['page_number']}]"

    return _REF.sub(_sub, body)


def refs_in_body(body: str) -> list[str]:
    return sorted(set(_REF.findall(body)), key=lambda r: int(r[1:]))


__all__ = [
    "DRAFT_PROMPT_VERSION",
    "Citation",
    "DraftOutput",
    "humanize_refs",
    "refs_in_body",
    "render_sections",
    "render_theses",
    "system_prompt",
    "user_prompt",
]
