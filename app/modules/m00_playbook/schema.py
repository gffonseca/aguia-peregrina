"""M0 Playbook — schema do arquivo `*.playbook.yaml` que a plataforma ingere.

O playbook é a "tese antes da máquina": um advogado-dono (OAB) escreve, versiona e aprova
a árvore de teses de uma tipologia **antes** de qualquer minuta ser gerada. Este módulo:

- define o modelo pydantic do playbook (fonte única do JSON Schema em
  `playbooks/playbook.schema.json`, gerado por `export_json_schema()`);
- valida um arquivo YAML (`validate_playbook(path)`), incluindo regras que o JSON Schema
  não expressa: ids únicos, referências cruzadas entre teses/seções/checagens e a regra
  de que um playbook só pode estar `aprovado` com registro de OAB + timestamp e com toda
  citação legal conferida;
- converte cada tese do playbook em `(Thesis, ThesisVersion)` pela função
  `to_thesis_payloads()`, para o serviço de M0 (`create_version`).
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0"
A_CONFERIR = "[A CONFERIR pelo advogado-dono]"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PlaybookStatus(StrEnum):
    rascunho = "rascunho"
    em_revisao = "em_revisao"
    aprovado = "aprovado"
    superado = "superado"


class Lado(StrEnum):
    defesa = "defesa"
    autor = "autor"


class Operador(StrEnum):
    """Operadores das condições de aplicação, avaliados sobre campos do dossiê (M5)."""

    igual = "=="
    diferente = "!="
    maior = ">"
    maior_igual = ">="
    menor = "<"
    menor_igual = "<="
    em = "in"
    nao_em = "not_in"
    existe = "existe"
    nao_existe = "nao_existe"
    contem = "contem"
    nao_contem = "nao_contem"


class CategoriaTese(StrEnum):
    preliminar = "preliminar"
    prejudicial = "prejudicial"
    merito = "merito"
    subsidiaria = "subsidiaria"
    processual = "processual"
    sinal = "sinal"  # não é argumento da peça; é um sinal para o revisor (ex.: predatória)


class TipoCampo(StrEnum):
    texto = "texto"
    numero = "numero"
    booleano = "booleano"
    data = "data"
    lista = "lista"
    valor_monetario = "valor_monetario"


class OrigemCampo(StrEnum):
    extracao = "extracao"  # M2/M5: extraído dos autos por LLM
    subsidio = "subsidio"  # M3: vindo do cliente (ERP/contrato/logs)
    publicacao = "publicacao"  # M1/M9
    antifraude = "antifraude"  # M4
    calculado = "calculado"  # derivado na esteira


class AcaoExcecao(StrEnum):
    nao_gerar_minuta = "nao_gerar_minuta"
    escalar_socio = "escalar_socio"
    sinalizar_acordo = "sinalizar_acordo"
    pedir_subsidio = "pedir_subsidio"
    alertar_revisor = "alertar_revisor"


class Severidade(StrEnum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"


# ---------------------------------------------------------------------------
# Blocos
# ---------------------------------------------------------------------------


class Metadata(_Strict):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$", description="slug único do playbook")
    nome: str
    tipologia: str = Field(
        pattern=r"^[a-z0-9_]{3,60}$",
        description="valor gravado em cases.typology / theses.typology",
    )
    tribunal: str = Field(pattern=r"^[A-Z]{2,6}[0-9]{0,2}$", description="TJPA, TRT8…")
    reu_tipo: str = Field(description="ex.: instituicao_financeira_regional")
    lado: Lado = Lado.defesa
    tipo_peca_padrao: str = Field(default="contestacao", description="drafts.draft_type")
    versao: int = Field(ge=1)
    supera_versao: int | None = Field(default=None, ge=1)
    autor_nome: str
    autor_oab: str = Field(pattern=r"^[A-Z]{2}\s?\d{1,6}[A-Z]?$", description="formato 'PA 12724'")
    criado_em: datetime
    status: PlaybookStatus = PlaybookStatus.rascunho
    aprovado_por_nome: str | None = None
    aprovado_por_oab: str | None = Field(default=None, pattern=r"^[A-Z]{2}\s?\d{1,6}[A-Z]?$")
    aprovado_em: datetime | None = None
    descricao: str | None = None
    observacoes: str | None = None

    @model_validator(mode="after")
    def _aprovacao_coerente(self) -> Metadata:
        if self.status == PlaybookStatus.aprovado:
            if not (self.aprovado_por_oab and self.aprovado_em):
                raise ValueError(
                    "status 'aprovado' exige aprovado_por_oab e aprovado_em "
                    "(registro OAB + timestamp)"
                )
            if self.aprovado_em < self.criado_em:
                raise ValueError("aprovado_em não pode ser anterior a criado_em")
        return self


class AssuntoCnj(_Strict):
    codigo: str = Field(pattern=r"^\d{1,6}$")
    nome: str
    conferido: bool = False


class GatilhosClassificacao(_Strict):
    """Como M1/M9 reconhecem que um processo pertence a esta tipologia."""

    assuntos_cnj: list[AssuntoCnj] = Field(min_length=1)
    classes_cnj: list[AssuntoCnj] = Field(default_factory=list)
    palavras_chave: list[str] = Field(min_length=1)
    palavras_que_excluem: list[str] = Field(default_factory=list)
    confianca_minima: float = Field(default=0.8, ge=0, le=1)


class CampoDossie(_Strict):
    campo: str = Field(pattern=r"^[a-z][a-z0-9_.]{1,80}$")
    tipo: TipoCampo
    origem: OrigemCampo
    descricao: str
    obrigatorio: bool = True
    bloqueia_minuta_se_ausente: bool = False


class Condicao(_Strict):
    campo: str
    operador: Operador
    valor: Any = None
    nota: str | None = None

    @model_validator(mode="after")
    def _valor_coerente(self) -> Condicao:
        sem_valor = {Operador.existe, Operador.nao_existe}
        if self.operador in sem_valor and self.valor is not None:
            raise ValueError(f"operador {self.operador} não aceita 'valor'")
        if self.operador not in sem_valor and self.valor is None:
            raise ValueError(f"operador {self.operador} exige 'valor'")
        return self


class Prova(_Strict):
    tipo_documento: str = Field(description="valor de documents.kind / document_pages.page_type")
    descricao: str
    origem: OrigemCampo = OrigemCampo.subsidio
    obrigatoria: bool = True
    peso: float = Field(default=1.0, ge=0, le=1, description="peso no score de evidência (M6)")


class ReferenciaLegal(_Strict):
    """Dispositivo, súmula, tema ou precedente. `conferido=False` até o advogado validar."""

    ref: str
    tipo: Literal["dispositivo", "sumula", "tema", "precedente", "doutrina", "norma_regulatoria"]
    para_que_serve: str
    conferido: bool = False
    nota: str = A_CONFERIR


class Fundamentacao(_Strict):
    dispositivos: list[ReferenciaLegal] = Field(default_factory=list)
    precedentes: list[ReferenciaLegal] = Field(default_factory=list)
    argumentos_chave: list[str] = Field(min_length=1)


class Tese(_Strict):
    id: str = Field(pattern=r"^T[0-9]{2}(\.[0-9]{1,2})*$", description="T01, T01.1…")
    nome: str
    categoria: CategoriaTese
    ordem: int = Field(ge=1)
    pai: str | None = Field(default=None, description="id da tese-mãe (theses.parent_id)")
    resumo: str
    condicoes_aplicacao: list[Condicao] = Field(
        min_length=1, description="conjunção (AND) sobre campos do dossiê"
    )
    provas_necessarias: list[Prova] = Field(default_factory=list)
    provas_que_afastam: list[Prova] = Field(default_factory=list)
    fundamentacao: Fundamentacao
    pedidos: list[str] = Field(min_length=1)
    pedidos_subsidiarios: list[str] = Field(default_factory=list)
    risco_se_mal_aplicada: str | None = None
    ativa: bool = True


class Excecao(_Strict):
    id: str = Field(pattern=r"^X[0-9]{2}$")
    descricao: str
    condicoes: list[Condicao] = Field(min_length=1)
    acao: AcaoExcecao
    nota: str | None = None


class FaixaAcordo(_Strict):
    grupo_comarcas: str
    comarcas: list[str] = Field(min_length=1)
    valor_min: float = Field(ge=0)
    valor_max: float = Field(ge=0)
    moeda: Literal["BRL"] = "BRL"
    base: str = Field(description="como a faixa foi obtida (ex.: média de condenação na carteira)")
    calibrar: bool = True

    @model_validator(mode="after")
    def _faixa(self) -> FaixaAcordo:
        if self.valor_max < self.valor_min:
            raise ValueError("valor_max < valor_min")
        return self


class RegraAcordo(_Strict):
    condicoes: list[Condicao] = Field(min_length=1)
    racional: str


class Alcada(_Strict):
    ate_valor: float = Field(ge=0)
    aprovador: str


class SinaisAcordo(_Strict):
    politica: str
    quando_acordar: list[RegraAcordo] = Field(min_length=1)
    quando_nao_acordar: list[RegraAcordo] = Field(default_factory=list)
    faixas_valor: list[FaixaAcordo] = Field(min_length=1)
    alcadas: list[Alcada] = Field(min_length=1)
    decisao_final: str = "A decisão de acordar é do advogado/cliente; a plataforma só sinaliza."


class ChecagemAntifraude(_Strict):
    codigo: str = Field(
        pattern=r"^[a-z][a-z0-9_]{2,60}$", description="fraud_checks.check_code (M4)"
    )
    descricao: str
    parametros: dict[str, Any] = Field(default_factory=dict)
    severidade: Severidade = Severidade.medium
    evidencia_esperada: str
    implementada_em_m4: bool = False
    calibrar: bool = True


class Antifraude(_Strict):
    regra_inviolavel: str = (
        "Nenhuma checagem produz rótulo de 'fraudador'; só flags com evidência. "
        "Apenas decisão humana registrada com OAB (human_decide) confirma um flag."
    )
    checagens: list[ChecagemAntifraude] = Field(min_length=1)


class SecaoPeca(_Strict):
    ordem: int = Field(ge=1)
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,60}$")
    titulo: str
    obrigatoria: bool = True
    teses_vinculadas: list[str] = Field(default_factory=list)
    instrucoes: str
    exige_citacao_de_pagina: bool = False


class ModeloPeca(_Strict):
    tipo: str = "contestacao"
    formato_saida: Literal["markdown", "docx"] = "markdown"
    regra_citacao: str = (
        "Toda afirmação de fato cita document_page_id (draft_citations). Sem página, sem afirmação."
    )
    secoes: list[SecaoPeca] = Field(min_length=3)
    estilo: list[str] = Field(default_factory=list)


class ItemChecklist(_Strict):
    id: str = Field(pattern=r"^R[0-9]{2}$")
    item: str
    bloqueante: bool = True


class CriteriosRevisao(_Strict):
    tempo_minimo_segundos: int = Field(ge=60, description="REVIEW_MIN_SECONDS_<tipo> (M7)")
    papel_minimo_revisor: Literal["lawyer", "partner"] = "lawyer"
    exige_segunda_revisao_se: list[Condicao] = Field(default_factory=list)
    checklist: list[ItemChecklist] = Field(min_length=3)
    motivos_recusa_padrao: list[str] = Field(min_length=1)


class Metrica(_Strict):
    id: str = Field(pattern=r"^M[0-9]{2}$")
    nome: str
    definicao: str
    meta: str
    fonte: str


class Playbook(_Strict):
    """Raiz do arquivo `*.playbook.yaml`."""

    schema_version: Literal["1.0"]
    metadata: Metadata
    gatilhos_classificacao: GatilhosClassificacao
    campos_dossie_obrigatorios: list[CampoDossie] = Field(min_length=1)
    teses: list[Tese] = Field(min_length=1)
    excecoes: list[Excecao] = Field(default_factory=list)
    sinais_acordo: SinaisAcordo
    antifraude: Antifraude
    modelo_peca: ModeloPeca
    criterios_revisao: CriteriosRevisao
    metricas: list[Metrica] = Field(min_length=1)

    # -- validações cruzadas -------------------------------------------------

    @model_validator(mode="after")
    def _integridade(self) -> Playbook:
        erros: list[str] = []

        ids_teses = [t.id for t in self.teses]
        dup = {i for i in ids_teses if ids_teses.count(i) > 1}
        if dup:
            erros.append(f"ids de tese duplicados: {sorted(dup)}")
        conjunto = set(ids_teses)
        for t in self.teses:
            if t.pai is not None and t.pai not in conjunto:
                erros.append(f"tese {t.id} aponta pai inexistente {t.pai}")
            if t.pai == t.id:
                erros.append(f"tese {t.id} é pai de si mesma")

        campos = {c.campo for c in self.campos_dossie_obrigatorios}
        cond_campos = {c.campo for t in self.teses for c in t.condicoes_aplicacao}
        cond_campos |= {c.campo for x in self.excecoes for c in x.condicoes}
        cond_campos |= {c.campo for r in self.sinais_acordo.quando_acordar for c in r.condicoes}
        cond_campos |= {c.campo for r in self.sinais_acordo.quando_nao_acordar for c in r.condicoes}
        cond_campos |= {c.campo for c in self.criterios_revisao.exige_segunda_revisao_se}
        faltam = sorted(cond_campos - campos)
        if faltam:
            erros.append(
                "condições referenciam campos que não estão em campos_dossie_obrigatorios: "
                f"{faltam}"
            )

        for s in self.modelo_peca.secoes:
            for tid in s.teses_vinculadas:
                if tid not in conjunto:
                    erros.append(f"seção {s.id} vincula tese inexistente {tid}")
        ordens = [s.ordem for s in self.modelo_peca.secoes]
        if len(ordens) != len(set(ordens)):
            erros.append("ordens de seção repetidas em modelo_peca")

        for grupo, lista in (
            ("excecoes", [x.id for x in self.excecoes]),
            ("checklist", [i.id for i in self.criterios_revisao.checklist]),
            ("metricas", [m.id for m in self.metricas]),
            ("antifraude", [c.codigo for c in self.antifraude.checagens]),
        ):
            if len(lista) != len(set(lista)):
                erros.append(f"ids duplicados em {grupo}")

        if self.metadata.status == PlaybookStatus.aprovado:
            nao_conferidas = [
                r.ref
                for t in self.teses
                for r in (*t.fundamentacao.dispositivos, *t.fundamentacao.precedentes)
                if not r.conferido
            ]
            if nao_conferidas:
                erros.append(
                    "playbook 'aprovado' com referências legais não conferidas: "
                    f"{nao_conferidas[:5]}{'…' if len(nao_conferidas) > 5 else ''}"
                )
            if any(not a.conferido for a in self.gatilhos_classificacao.assuntos_cnj):
                erros.append("playbook 'aprovado' com assuntos CNJ não conferidos")

        if erros:
            raise ValueError("; ".join(erros))
        return self

    # -- utilidades ---------------------------------------------------------

    def referencias_nao_conferidas(self) -> list[str]:
        return [
            f"{t.id}: {r.ref}"
            for t in self.teses
            for r in (*t.fundamentacao.dispositivos, *t.fundamentacao.precedentes)
            if not r.conferido
        ]

    def tese(self, tese_id: str) -> Tese:
        for t in self.teses:
            if t.id == tese_id:
                return t
        raise KeyError(tese_id)


# ---------------------------------------------------------------------------
# Carga / validação / exportação
# ---------------------------------------------------------------------------


class PlaybookValidationError(ValueError):
    pass


def load_playbook(path: str | Path) -> Playbook:
    """Lê e valida um `*.playbook.yaml`. Levanta PlaybookValidationError com mensagem legível."""
    p = Path(path)
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PlaybookValidationError(f"{p}: YAML inválido: {exc}") from exc
    if not isinstance(raw, dict):
        raise PlaybookValidationError(f"{p}: raiz do YAML deve ser um mapeamento")
    try:
        return Playbook.model_validate(raw)
    except Exception as exc:  # pydantic.ValidationError é ValueError
        raise PlaybookValidationError(f"{p}: {exc}") from exc


def validate_playbook(path: str | Path) -> Playbook:
    """Alias semântico de `load_playbook` para uso em CLI/CI."""
    return load_playbook(path)


def export_json_schema() -> dict[str, Any]:
    schema = Playbook.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://aguia-peregrina.fbs.adv.br/schemas/playbook-1.0.json"
    schema["title"] = "Águia Peregrina — Playbook de teses (M0)"
    return schema


def write_json_schema(path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(export_json_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def to_thesis_payloads(pb: Playbook) -> list[dict[str, Any]]:
    """Converte o playbook em payloads para `theses` + `thesis_versions` (M0 service).

    Um item por tese: `typology`, `code`, `title`, `parent_code`, `body_markdown`,
    `conditions` (condições + provas + pedidos, como o M6 consome), `author_oab`.
    """
    out: list[dict[str, Any]] = []
    for t in pb.teses:
        corpo = [f"# {t.id} — {t.nome}", "", t.resumo, "", "## Argumentos"]
        corpo += [f"- {a}" for a in t.fundamentacao.argumentos_chave]
        corpo += ["", "## Fundamentação (conferir cada item)"]
        corpo += [
            f"- {r.tipo}: {r.ref} — {r.para_que_serve}" + ("" if r.conferido else f" {A_CONFERIR}")
            for r in (*t.fundamentacao.dispositivos, *t.fundamentacao.precedentes)
        ]
        corpo += ["", "## Pedidos"] + [f"- {p}" for p in t.pedidos]
        if t.pedidos_subsidiarios:
            corpo += ["", "## Pedidos subsidiários"] + [f"- {p}" for p in t.pedidos_subsidiarios]
        out.append(
            {
                "typology": pb.metadata.tipologia,
                "code": t.id,
                "title": t.nome,
                "parent_code": t.pai,
                "body_markdown": "\n".join(corpo),
                "conditions": {
                    "categoria": t.categoria.value,
                    "ordem": t.ordem,
                    "condicoes_aplicacao": [
                        c.model_dump(mode="json") for c in t.condicoes_aplicacao
                    ],
                    "provas_necessarias": [p.model_dump(mode="json") for p in t.provas_necessarias],
                    "provas_que_afastam": [p.model_dump(mode="json") for p in t.provas_que_afastam],
                    "pedidos_subsidiarios": t.pedidos_subsidiarios,
                    "playbook_id": pb.metadata.id,
                    "playbook_versao": pb.metadata.versao,
                },
                "author_oab": pb.metadata.autor_oab,
            }
        )
    return out


if (
    __name__ == "__main__"
):  # pragma: no cover - uso manual: python -m app.modules.m00_playbook.schema
    import sys

    for arg in sys.argv[1:]:
        pb = validate_playbook(arg)
        pend = pb.referencias_nao_conferidas()
        print(
            f"OK {arg}: {len(pb.teses)} teses, status={pb.metadata.status}, "
            f"{len(pend)} referências a conferir"
        )
