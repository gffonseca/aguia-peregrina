"""Tabela de remuneração por ato do contrato BASA FB1798 e reconhecimento de atos.

O texto do ato chega com grafias variadas ("Petições Interlocutórias", "Atos BASA - Petições
interlocutórias", "Recursos apelação ... iniminado"). `reconhecer_ato` devolve o ato canônico da
tabela por regras ordenadas sobre o texto normalizado; o que não casar fica sem enquadramento e
vira erro na pré-auditoria (nunca chuta um valor).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

Coluna = Literal["trabalhista", "jec", "rec_cred", "demais", "adm"]
COLUNAS: tuple[Coluna, ...] = ("trabalhista", "jec", "rec_cred", "demais", "adm")
ROTULO_COLUNA: dict[str, str] = {
    "trabalhista": "Trabalhista",
    "jec": "JEC/JEF",
    "rec_cred": "Recuperação de crédito",
    "demais": "Demais feitos",
    "adm": "Administrativo",
}

_TABELA_PATH = Path(__file__).with_name("tabela_fb1798.yaml")


@dataclass(frozen=True)
class Ato:
    id: str
    nome: str
    valores: dict[str, float | None]
    resultado: bool = False

    def valor(self, coluna: str) -> float | None:
        return self.valores.get(coluna)


@dataclass(frozen=True)
class Tabela:
    contrato: str
    atos: dict[str, Ato]
    nao_remunerados: dict[str, tuple[str, ...]]


@lru_cache
def carregar_tabela(path: str | None = None) -> Tabela:
    raw = yaml.safe_load(Path(path or _TABELA_PATH).read_text(encoding="utf-8"))
    atos = {}
    for a in raw["atos"]:
        atos[a["id"]] = Ato(
            id=a["id"],
            nome=a["nome"],
            valores={c: a.get(c) for c in COLUNAS},
            resultado=bool(a.get("resultado", False)),
        )
    nr = {n["id"]: tuple(n["termos"]) for n in raw["nao_remunerados"]}
    return Tabela(contrato=raw["contrato"], atos=atos, nao_remunerados=nr)


def normalizar(texto: str | None) -> str:
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"^\s*atos\s+basa\s*-\s*", "", t)
    t = re.sub(r"[^a-z0-9/;:()\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# Regras em ordem de especificidade: a primeira que casar vence.
_REGRAS: tuple[tuple[str, str], ...] = (
    (r"extincao", "extincao_1grau"),
    (
        r"juntada.*(planilha|custas|deposito|guia)|(planilha|custas|guias?).*juntada",
        "juntada_planilha_custas",
    ),
    (r"interlocut", "peticao_interlocutoria"),
    (r"contrarraz|contra raz", "contrarrazoes"),
    (r"resposta.*impugnacao.*valor da causa", "resposta_impugnacao_valor_causa"),
    (r"respostas? a agravos?.*(inominado|regimental|interno)", "resposta_agravo_interno"),
    (r"respostas? a agravo", "resposta_agravo_instrumento"),
    (r"impugnacao.*embargos.*(arrematacao|adjudicacao)", "impugnacao_embargos_arrematacao"),
    (r"impugnacao.*embargos", "impugnacao_embargos_execucao"),
    (r"impugnacao.*(gratuidade|assistencia judiciaria|justica gratuita)", "impugnacao_gratuidade"),
    (r"impugnacao.*cumprimento", "impugnacao_cumprimento"),
    (r"impugnacao.*valor do credito", "impugnacao_valor_credito"),
    (r"impugnacao.*valor da causa|incidente de falsidade", "impugnacao_valor_causa"),
    (r"impugnacao.*calculo", "impugnacao_calculos"),
    (r"impugnacao.*laudo", "impugnacao_laudo"),
    (r"embargos de declaracao", "embargos_declaracao"),
    (r"embargos.*(arrematacao|adjudicacao)", "embargos_arrematacao"),
    (r"embargos.*(divergencia|infringente)", "embargos_divergencia"),
    (r"embargos.*(execucao|monitoria|terceiro)", "embargos_execucao"),
    (r"pre executividade|pre-executividade", "excecao_pre_executividade"),
    (r"excecao.*(impedimento|incompetencia|suspeicao)", "excecao_impedimento"),
    (r"agravo retido", "agravo_retido"),
    (r"agravos?.*(inominado|regimental|interno)", "agravo_interno"),
    (r"agravo", "agravo_instrumento"),
    (
        r"apelacao|recurso especial|recurso extraordinario|recursos? (adesivo|ordinario|inominado)",
        "apelacao",
    ),
    (r"contestacao|defesa trabalhista|^defesa$", "contestacao"),
    (r"replica", "replica"),
    (r"reconvencao", "reconvencao"),
    (r"memoriais|razoes finais", "memoriais"),
    (r"sustentacao oral", "sustentacao_oral"),
    (r"informacoes.*mandado de seguranca", "informacoes_ms"),
    (r"mandado de seguranca", "mandado_seguranca"),
    (r"audiencia.*juizado", "audiencia_jec"),
    (r"audiencia.*extrajudicial", "audiencia_extrajudicial"),
    (r"audiencia.*sem instrucao", "audiencia_conciliacao"),
    (r"audiencia.*(instrucao)", "audiencia_instrucao"),
    (r"audiencia", "audiencia_conciliacao"),
    (r"ajuizamento|peticao inicial|distribuicao da acao", "ajuizamento"),
    (r"carta precatoria", "carta_precatoria"),
    (r"citacao", "citacao_efetivada"),
    (r"arresto|penhora", "arresto_penhora"),
    (r"indisponibilidade", "indisponibilidade_bens"),
    (r"busca e apreensao", "busca_apreensao"),
    (r"imissao|reintegracao de posse", "imissao_posse"),
    (r"praca.*sem|leilao.*negativo|sem arrematacao", "praca_sem_arrematacao"),
    (r"praca|arrematacao|adjudicacao", "praca_com_arrematacao"),
    (r"habilitacao de credito", "habilitacao_credito"),
    (r"restituicao.*falencia", "restituicao_falencia"),
    (r"quesitos", "quesitos"),
    (r"pericia|inspecao", "pericia_acompanhamento"),
    (r"interpelacao|notificacao judicial|protesto judicial", "interpelacao"),
    (r"procon", "procon"),
    (r"carga de autos|extracao de copias", "diligencia_carga"),
    (r"comprovacao de interposicao de agravo", "diligencia_comprovacao_agravo"),
    (r"protocolo de peca", "diligencia_protocolo_peca_banco"),
    (r"nao terceirizado", "diligencia_analise_nao_terceirizado"),
    (r"cartorio|diligencia", "diligencia_cartorio"),
)
_REGRAS_RX = tuple((re.compile(p), a) for p, a in _REGRAS)


def reconhecer_ato(texto: str | None) -> str | None:
    t = normalizar(texto)
    if not t:
        return None
    for rx, ato in _REGRAS_RX:
        if rx.search(t):
            return ato
    return None


def nao_remunerado(texto: str | None, tabela: Tabela | None = None) -> str | None:
    """Devolve o id da hipótese de ato não remunerado (preâmbulo do Anexo I), se houver."""
    t = normalizar(texto)
    tab = tabela or carregar_tabela()
    for nid, termos in tab.nao_remunerados.items():
        if any(normalizar(x) in t for x in termos):
            return nid
    return None


_REC_CRED = re.compile(
    r"execucao|monitoria|cobranca|cumprimento|busca e apreensao|precatoria|"
    r"habilitacao|falencia|recuperacao judicial|inventario|insolvencia"
)
_JEC = re.compile(r"juizado|jec|jef|procedimento do juizado")
_ADM = re.compile(r"administrativ|procon")


def enquadrar_coluna(acao: str | None, ficha: str | None, cnj: str | None) -> str:
    """Natureza do feito → coluna da tabela. Trabalhista pela ficha (TRAB.) ou justiça 5 no CNJ."""
    f = (ficha or "").upper()
    digitos = re.sub(r"\D", "", cnj or "")
    if f.startswith("TRAB") or (len(digitos) == 20 and digitos[13] == "5"):
        return "trabalhista"
    a = normalizar(acao)
    if _ADM.search(a):
        return "adm"
    if _JEC.search(a):
        return "jec"
    if _REC_CRED.search(a):
        return "rec_cred"
    return "demais"
