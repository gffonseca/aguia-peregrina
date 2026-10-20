"""Pré-auditoria da prestação de contas mensal (contrato BASA FB1798) antes do envio à CCONS.

Cada linha recebe um status:
- OK        → vai para o Anexo II.
- ALERTA    → vai para o Anexo II, mas precisa de conferência humana (risco de glosa).
- BLOQUEIO  → não vai para o Anexo II até ser corrigida (glosa certa ou erro de dado).

Regras (código → status):
- ATO_NAO_RECONHECIDO (BLOQUEIO): texto do ato não corresponde a nenhum ato da tabela.
- ATO_NAO_REMUNERADO (BLOQUEIO): habilitação, renúncia, ciência, reiteração etc. (preâmbulo).
- NA_NA_COLUNA (BLOQUEIO): o ato é N/A em todas as colunas compatíveis com o feito.
- COLUNA_PRESUMIDA (ALERTA): N/A na coluna presumida pela ação, mas previsto em outra (ex.:
  contestação do Banco numa "Cobrança" movida contra ele → Demais feitos).
- COLUNA_DIVERGENTE (ALERTA): o valor declarado é o de outra coluna da tabela (ex.: R$ 104 de
  contestação no juizado); confirmar a natureza do feito.
- VALOR_ACIMA_DA_TABELA / VALOR_ABAIXO_DA_TABELA (ALERTA): declarado ≠ tabela; o Anexo II
  sai com o valor da tabela.
- SEM_VALOR (BLOQUEIO): linha sem valor.
- FORA_DA_COMPETENCIA (BLOQUEIO): data do protocolo fora do mês da prestação.
- SEM_DATA (BLOQUEIO).
- DUPLICADO (BLOQUEIO): mesma ficha, mesmo ato, mesma data — a tabela paga um único ato.
- REPETIDO_NO_MES (ALERTA): mesma ficha e mesmo ato em datas diferentes no mês (risco de ser
  lido como reiteração; anexar as peças).
- CNJ_INVALIDO (ALERTA): número fora do padrão CNJ ou dígito verificador errado.
- FICHA_TROCADA (ALERTA): o processo está no Benner sob outra ficha (sugere a correta).
- FICHA_FORA_DO_BENNER / FICHA_ENCERRADA / CNJ_DIVERGE_BENNER (ALERTA): só com a base do Benner.
- RECURSO_SUPERIOR (ALERTA): REsp/RE em feito cível — a Especialidade II só lista apelação,
  adesivo, ordinário e inominado; confirmar o enquadramento com a CCONS.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.core import cnj as cnjlib
from app.modules.m12_faturamento.tabela import (
    ROTULO_COLUNA,
    Tabela,
    carregar_tabela,
    enquadrar_coluna,
    nao_remunerado,
    normalizar,
    reconhecer_ato,
)

SEVERIDADE = {"OK": 0, "ALERTA": 1, "BLOQUEIO": 2}


def _dig(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


@dataclass
class LinhaAto:
    ficha: str
    cnj: str
    comarca: str
    uf: str
    acao: str
    parte_adversa: str
    ato_texto: str
    data: date | None
    valor: float | None
    origem: int = 0  # linha da planilha de origem


@dataclass
class Achado:
    codigo: str
    status: str
    detalhe: str


@dataclass
class LinhaAuditada:
    linha: LinhaAto
    ato_id: str | None
    ato_nome: str | None
    coluna: str
    valor_tabela: float | None
    resultado: bool
    achados: list[Achado] = field(default_factory=list)
    ficha_sugerida: str | None = None

    @property
    def chave(self) -> str:
        """Processo (dígitos do CNJ) como chave; ficha quando não há número."""
        return _dig(self.linha.cnj) or self.linha.ficha

    @property
    def status(self) -> str:
        if not self.achados:
            return "OK"
        return max((a.status for a in self.achados), key=SEVERIDADE.__getitem__)

    @property
    def valor_faturavel(self) -> float:
        """Valor que entra no Anexo II: o da tabela quando há; senão o declarado."""
        if self.status == "BLOQUEIO":
            return 0.0
        if any(a.codigo == "COLUNA_DIVERGENTE" for a in self.achados):
            return float(self.linha.valor or 0)  # dúvida de enquadramento: não presume a maior
        if self.valor_tabela is not None:
            return float(self.valor_tabela)
        return float(self.linha.valor or 0)


@dataclass
class FichaBenner:
    ficha: str
    cnj: str
    situacao: str


def _uf(texto: str) -> str:
    t = normalizar(texto)
    if t.startswith("amazon") or t == "am":
        return "AM"
    if t.startswith("par") or t == "pa":
        return "PA"
    return (texto or "").strip().upper()[:2]


def auditar(
    linhas: list[LinhaAto],
    competencia: str,
    benner: dict[str, FichaBenner] | None = None,
    tabela: Tabela | None = None,
) -> list[LinhaAuditada]:
    """`competencia` = 'AAAA-MM'. `benner` = fichas exportadas do Benner indexadas pelo código."""
    tab = tabela or carregar_tabela()
    por_cnj = {_dig(f.cnj): f for f in (benner or {}).values() if _dig(f.cnj)}
    ano, mes = (int(x) for x in competencia.split("-"))
    out: list[LinhaAuditada] = []
    for ln in linhas:
        ln.uf = _uf(ln.uf)
        ato_id = reconhecer_ato(ln.ato_texto)
        ato = tab.atos.get(ato_id) if ato_id else None
        coluna = enquadrar_coluna(ln.acao, ln.ficha, ln.cnj)
        valor_tab = ato.valor(coluna) if ato else None
        coluna_presumida: str | None = None
        if ato is not None and valor_tab is None and coluna != "trabalhista":
            # Ex.: contestação do Banco numa "Cobrança" movida contra ele → Demais feitos.
            for alt in ("demais", "rec_cred", "jec"):
                if ato.valor(alt) is not None:
                    coluna_presumida, coluna, valor_tab = coluna, alt, ato.valor(alt)
                    break
        la = LinhaAuditada(
            linha=ln,
            ato_id=ato_id,
            ato_nome=ato.nome if ato else None,
            coluna=coluna,
            valor_tabela=valor_tab,
            resultado=bool(ato and ato.resultado),
        )
        nr = nao_remunerado(ln.ato_texto, tab)
        if nr:
            la.achados.append(Achado("ATO_NAO_REMUNERADO", "BLOQUEIO", f"hipótese: {nr}"))
        if ato is None:
            la.achados.append(Achado("ATO_NAO_RECONHECIDO", "BLOQUEIO", f"texto: {ln.ato_texto!r}"))
        elif coluna_presumida:
            la.achados.append(
                Achado(
                    "COLUNA_PRESUMIDA",
                    "ALERTA",
                    f"{ato.nome} é N/A em {ROTULO_COLUNA[coluna_presumida]} (ação: {ln.acao}); "
                    f"enquadrado em {ROTULO_COLUNA[coluna]} — confirmar a natureza do feito",
                )
            )
        elif valor_tab is None:
            cols = [ROTULO_COLUNA[c] for c, v in ato.valores.items() if v is not None]
            la.achados.append(
                Achado(
                    "NA_NA_COLUNA",
                    "BLOQUEIO",
                    f"{ato.nome} é N/A em {ROTULO_COLUNA[coluna]} (ação: {ln.acao}); "
                    f"previsto em: {', '.join(cols)}",
                )
            )
        if ln.valor is None:
            la.achados.append(Achado("SEM_VALOR", "BLOQUEIO", "linha sem valor"))
        elif (
            ato is not None
            and valor_tab is not None
            and abs(float(ln.valor) - float(valor_tab)) > 0.005
            and (
                outras := [
                    c
                    for c, v in ato.valores.items()
                    if v is not None and abs(float(v) - float(ln.valor)) < 0.005
                ]
            )
        ):
            la.achados.append(
                Achado(
                    "COLUNA_DIVERGENTE",
                    "ALERTA",
                    f"R$ {ln.valor:.2f} é o valor de {', '.join(ROTULO_COLUNA[c] for c in outras)};"
                    f" pela ação ({ln.acao}) seria {ROTULO_COLUNA[coluna]} R$ {valor_tab:.2f}"
                    " — confirmar a natureza do feito",
                )
            )
        elif valor_tab is not None and abs(float(ln.valor) - float(valor_tab)) > 0.005:
            acima = float(ln.valor) > float(valor_tab)
            la.achados.append(
                Achado(
                    "VALOR_ACIMA_DA_TABELA" if acima else "VALOR_ABAIXO_DA_TABELA",
                    "ALERTA",
                    f"declarado R$ {ln.valor:.2f} × tabela R$ {valor_tab:.2f} "
                    f"({ROTULO_COLUNA[coluna]})",
                )
            )
        if ln.data is None:
            la.achados.append(Achado("SEM_DATA", "BLOQUEIO", "sem data de protocolo"))
        elif (ln.data.year, ln.data.month) != (ano, mes):
            la.achados.append(
                Achado(
                    "FORA_DA_COMPETENCIA",
                    "BLOQUEIO",
                    f"protocolo em {ln.data:%d/%m/%Y}; prestação de {mes:02d}/{ano}",
                )
            )
        parsed = cnjlib.parse(ln.cnj)
        if ln.cnj and (parsed is None or not parsed.is_valid):
            la.achados.append(Achado("CNJ_INVALIDO", "ALERTA", f"{ln.cnj}"))
        t = normalizar(ln.ato_texto)
        if coluna != "trabalhista" and re.search(
            r"recurso especial|recurso extraordinario|\bresp\b|\bre\b", t
        ):
            la.achados.append(
                Achado(
                    "RECURSO_SUPERIOR",
                    "ALERTA",
                    "REsp/RE não aparece na Especialidade II; confirmar enquadramento",
                )
            )
        if benner is not None:
            fb = benner.get(ln.ficha)
            pelo_cnj = por_cnj.get(_dig(ln.cnj))
            if fb is not None and _dig(fb.cnj) == _dig(ln.cnj):
                pass
            elif pelo_cnj is not None:
                la.ficha_sugerida = pelo_cnj.ficha
                la.achados.append(
                    Achado(
                        "FICHA_TROCADA",
                        "ALERTA",
                        f"no Benner o processo {ln.cnj} é a ficha {pelo_cnj.ficha}"
                        + (f"; a ficha {ln.ficha} é o processo {fb.cnj}" if fb else ""),
                    )
                )
                fb = pelo_cnj
            elif fb is not None:
                la.achados.append(Achado("CNJ_DIVERGE_BENNER", "ALERTA", f"Benner: {fb.cnj}"))
            else:
                la.achados.append(
                    Achado(
                        "FICHA_FORA_DO_BENNER",
                        "ALERTA",
                        "nem a ficha nem o processo estão no Benner",
                    )
                )
            if fb is not None and normalizar(fb.situacao) == "encerrado":
                la.achados.append(Achado("FICHA_ENCERRADA", "ALERTA", "ficha encerrada no Benner"))
        out.append(la)

    # Duplicidade (precisa do conjunto)
    chave_dia = Counter((a.chave, a.ato_id, a.linha.data) for a in out if a.ato_id)
    por_mes: dict[tuple[str, str], set[Any]] = defaultdict(set)
    for a in out:
        if a.ato_id:
            por_mes[(a.chave, a.ato_id)].add(a.linha.data)
    vistos: set[tuple[Any, ...]] = set()
    for a in out:
        if not a.ato_id:
            continue
        k = (a.chave, a.ato_id, a.linha.data)
        if chave_dia[k] > 1:
            if k in vistos:
                a.achados.append(
                    Achado("DUPLICADO", "BLOQUEIO", "mesmo ato, mesmo processo, mesma data")
                )
            vistos.add(k)
        if len(por_mes[(a.chave, a.ato_id)]) > 1:
            a.achados.append(
                Achado(
                    "REPETIDO_NO_MES",
                    "ALERTA",
                    f"{len(por_mes[(a.chave, a.ato_id)])} protocolos do mesmo ato no mês",
                )
            )
    return out


def resumo(auditadas: list[LinhaAuditada]) -> dict[str, Any]:
    por_uf: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    regras: Counter[str] = Counter()
    for a in auditadas:
        u = por_uf[a.linha.uf]
        u["linhas"] += 1
        u["declarado"] += float(a.linha.valor or 0)
        u["faturavel"] += a.valor_faturavel
        u[f"n_{a.status}"] += 1
        if a.status == "BLOQUEIO":
            u["bloqueado"] += float(a.linha.valor or 0)
        for ac in a.achados:
            regras[ac.codigo] += 1
    return {
        "por_uf": {k: dict(v) for k, v in sorted(por_uf.items())},
        "regras": dict(regras.most_common()),
        "linhas": len(auditadas),
        "fichas": len({a.linha.ficha for a in auditadas}),
    }


def to_date(v: Any) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()[:10]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
