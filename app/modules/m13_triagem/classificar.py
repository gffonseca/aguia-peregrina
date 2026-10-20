"""Triagem da caixa basa@: classifica o e-mail, acha o processo e define quem precisa ver.

Regras, não IA: o que chega do BASA e dos tribunais é repetitivo e o custo de errar a área é
baixo (o resumo mostra tudo à coordenação de qualquer forma). Ordem de decisão:

1. Ruído (newsletter do Banco, Centro Cultural, marketing) → IGNORAR.
2. Tribunal (PROJUDI, PJe, e-SAJ, DJe, "intimação", "decurso de prazo") → INTIMACAO.
3. Assunto do contrato com o Banco: prestação/NF/pagamento/glosa → PRESTACAO_CONTAS;
   Benner/acesso/usuário → SISTEMA_BENNER; reunião/alinhamento → REUNIAO;
   pedido sobre processo (subsídio, custas, cálculo, acordo, CNJ citado) → PROCESSO.
4. Resto → OUTROS (coordenação decide).

Área (pela categoria) + processo (CNJ → ficha → UF) → papel. Os papéis (coordenacao,
financeiro, equipe_pa, equipe_am, prazos_pa, prazos_am) viram pessoas numa tabela editável.

O resumo também mede o problema das cadeias: quantas pessoas do escritório estavam no e-mail
e quantas precisavam estar.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.core import cnj as cnjlib

DOMINIOS_ESCRITORIO = ("fonsecabrasilserrao.com", "fonsecabrasil.com.br")

CATEGORIAS = (
    "INTIMACAO",
    "PRESTACAO_CONTAS",
    "PROCESSO",
    "SISTEMA_BENNER",
    "REUNIAO",
    "OUTROS",
    "IGNORAR",
)

_TRIBUNAIS = re.compile(
    r"projudi|pje|esaj|e-saj|tjam\.jus|tjpa\.jus|trt8|trt11|trf1|jus\.br|diario da justica|dje"
)
_RUIDO_REMETENTE = re.compile(r"basablog|comunicado|newsletter|no-?reply@(?!.*jus)|marketing")
_RUIDO_TEXTO = re.compile(
    r"centro cultural|exposic|programe-se|oficina|plano safra|desenrola|visualizar este e-mail"
)


def _n(t: str | None) -> str:
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", t)


@dataclass
class Email:
    id: str
    remetente: str
    assunto: str
    corpo: str
    para: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    recebido_em: str = ""
    link: str | None = None
    conversa: str | None = None


@dataclass
class Triagem:
    categoria: str
    urgencia: str  # alta | media | baixa
    papeis: list[str]
    cnjs: list[str]
    uf: str | None
    motivo: str
    acao: str
    internos_copiados: int
    internos_necessarios: int

    @property
    def excesso_copia(self) -> int:
        return max(self.internos_copiados - self.internos_necessarios, 0)


def cnjs_no_texto(texto: str) -> list[str]:
    vistos: list[str] = []
    for m in cnjlib.CNJ_IN_TEXT.finditer(texto or ""):
        d = re.sub(r"\D", "", m.group(0))
        p = cnjlib.parse(d)
        if p is not None and p.is_valid and d not in vistos:
            vistos.append(d)
    return vistos


def uf_do_cnj(d: str) -> str | None:
    p = cnjlib.parse(d)
    if p is None:
        return None
    if (p.segment, p.tribunal) in ((8, 14), (5, 8)):
        return "PA"
    if (p.segment, p.tribunal) in ((8, 4), (5, 11)):
        return "AM"
    return None


def _internos(e: Email) -> int:
    return sum(1 for x in {a.lower() for a in e.para + e.cc} if x.endswith(DOMINIOS_ESCRITORIO))


def classificar(
    e: Email, uf_por_cnj: dict[str, str] | None = None, carteira: set[str] | None = None
) -> Triagem:
    """`uf_por_cnj`: UF da ficha no Benner (dígitos do CNJ → 'PA'/'AM'), quando conhecida.
    `carteira`: CNJs (dígitos) das fichas do BASA; intimação de processo fora dela e sem o
    Banco no texto vai para os prazos gerais do escritório, não para a equipe do contrato."""
    rem, ass, corpo = _n(e.remetente), _n(e.assunto), _n(e.corpo)
    tudo = f"{ass} {corpo}"
    cnjs = cnjs_no_texto(f"{e.assunto}\n{e.corpo}")
    ufs = [(uf_por_cnj or {}).get(c) or uf_do_cnj(c) for c in cnjs]
    uf = next((u for u in ufs if u), None)
    sufixo = f"_{uf.lower()}" if uf else ""
    internos = _internos(e)

    def t(cat: str, urg: str, papeis: list[str], motivo: str, acao: str) -> Triagem:
        papeis = list(dict.fromkeys(papeis))
        return Triagem(cat, urg, papeis, cnjs, uf, motivo, acao, internos, len(papeis))

    if _RUIDO_REMETENTE.search(rem) or (_RUIDO_TEXTO.search(tudo) and not cnjs):
        return t("IGNORAR", "baixa", [], "comunicado/marketing", "nenhuma")

    if _TRIBUNAIS.search(rem) or re.search(r"intimac|decurso de prazo|publicac", ass):
        txt = re.sub(r"cumprimento de sentenca", "cumprimento", tudo)
        do_contrato = bool(
            re.search(r"banco da amazonia|\bbasa\b", txt)
            or (carteira and any(c in carteira for c in cnjs))
        )
        if do_contrato:
            papel = f"prazos{sufixo}" if uf else "prazos_pa"
        else:
            papel = "prazos_escritorio"
        alta = re.search(
            r"decurso de prazo|julgad|sentenc|acordao|pauta|sessao|liminar|prescric|"
            r"audiencia|penhora|bloqueio|extinc",
            txt,
        )
        if "decurso de prazo" in txt:
            acao = "conferir no sistema do tribunal se houve resposta; se não houve, peticionar"
        elif "prescric" in txt:
            acao = "manifestar contra a prescrição intercorrente"
        elif re.search(r"julgad|sentenc|acordao", txt):
            acao = "ler a decisão e avaliar recurso no prazo"
        elif re.search(r"pauta|sessao", txt):
            acao = "acompanhar o julgamento; avaliar memoriais ou sustentação"
        else:
            acao = "abrir a intimação, lançar o prazo e designar o responsável"
        if do_contrato and "conferir" not in acao and "acompanhar" not in acao:
            acao += " (ato cobrável no contrato BASA)"
        return t(
            "INTIMACAO",
            "alta" if alta else "media",
            [papel],
            "tribunal" + ("" if do_contrato else " — fora do contrato BASA"),
            acao,
        )

    do_banco = rem.endswith("basa.com.br") or "basa" in ass or "banco da amazonia" in tudo
    if re.search(
        r"prestac[ao]+ de contas|relatorio de atos|anexo ii|conformidade|glosa|nota fiscal|"
        r"\bnf\b|pagamento|faturament|honorarios.*(pag|repasse)|repasse",
        tudo,
    ):
        return t(
            "PRESTACAO_CONTAS",
            "alta" if re.search(r"glosa|pendenc|devolu|recus|atras", tudo) else "media",
            ["financeiro", "coordenacao"],
            "prestação de contas / pagamento",
            "atualizar o painel de recebíveis e responder pela coordenação",
        )
    if re.search(r"benner|usuario|acesso ao sistema|senha|login|perfil de acesso", tudo):
        return t(
            "SISTEMA_BENNER",
            "media",
            ["coordenacao"],
            "acesso/sistema do Banco",
            "coordenação responde; não precisa da equipe toda",
        )
    if re.search(r"reuniao|alinhamento|teams\.microsoft|convite|agenda", tudo):
        return t(
            "REUNIAO",
            "media",
            ["coordenacao"],
            "reunião",
            "coordenação confirma e repassa só a quem vai participar",
        )
    if cnjs or (
        do_banco
        and re.search(r"subsidio|custas|calculo|acordo|proposta|ficha|processo|prazo", tudo)
    ):
        return t(
            "PROCESSO",
            "alta" if re.search(r"urgente|prazo|hoje|imediat", tudo) else "media",
            [f"equipe{sufixo}" if uf else "coordenacao"],
            "pedido sobre processo",
            "responsável pela ficha responde e anexa no Benner",
        )
    return t("OUTROS", "baixa", ["coordenacao"], "não classificado", "coordenação decide")
