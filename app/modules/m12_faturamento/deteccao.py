"""Motor de oportunidades — detecção real a partir dos movimentos do processo (DataJud / TPU).

Cada movimento (código TPU + nome + complementos tabelados) vira zero ou mais *eventos* do
catálogo `gatilhos_fb1798.yaml`. Cada evento abre uma *oportunidade*: o ato cabível, o valor da
tabela na coluna do feito, o prazo de referência e o papel da IA. Depois, `conciliar` cruza as
oportunidades com os atos já cobrados nas prestações de contas e marca cada uma como
ATENDIDA (ato cobrado no prazo), PERDIDA (prazo vencido sem ato cobrado) ou ABERTA.

Limites conhecidos do DataJud: não diz quem peticionou, não traz o texto da decisão nem o tipo
do mandado. Por isso alguns eventos saem com `confianca='media'` e pedem confirmação humana
(ex.: mandado cumprido pode ser de citação ou de penhora).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from app.modules.m12_faturamento.tabela import (
    carregar_gatilhos,
    carregar_tabela,
    enquadrar_coluna,
    normalizar,
)

# --- polo do Banco pela classe processual --------------------------------------------------

_ATIVO = re.compile(r"execucao|monitoria|cumprimento|precatoria|busca e apreensao|cobranca")
_EMBARGADO = re.compile(r"embargos")


def polo_do_banco(classe_nome: str | None) -> str:
    """'autor' (Banco cobra), 'embargado' (devedor embarga) ou 'reu' (ação contra o Banco)."""
    c = normalizar(classe_nome)
    if _EMBARGADO.search(c):
        return "embargado"
    if _ATIVO.search(c):
        return "autor"
    return "reu"


# --- regras movimento → evento ------------------------------------------------------------

SENT_PROCEDENCIA = {219, 221}
SENT_IMPROCEDENCIA = {220}
SENT_TERMINATIVA_CONTRA_AUTOR = {454, 458, 459, 461, 471, 12259, 12325}
EXTINCAO_PAGAMENTO = {196, 1049}
EXTINCAO_ACORDO = {466, 14099, 12187}
EXTINCAO_DESISTENCIA = {463}
ACORDAO_DESFAVORAVEL_AO_RECORRENTE = {239, 235, 242}  # não provimento / não conhecimento
ARQUIVO_DEFINITIVO = {246, 22}
ARQUIVO_PROVISORIO = {245}
DECISAO_A_CUMPRIR = {12185, 12164, 11010, 11383}


@dataclass(frozen=True)
class Evento:
    nome: str
    data: date
    movimento: str
    confianca: str = "alta"  # alta | media


def _comps(m: dict[str, Any]) -> list[str]:
    return [normalizar(c.get("nome")) for c in (m.get("complementosTabelados") or [])]


def _data(m: dict[str, Any]) -> date | None:
    s = (m.get("dataHora") or "")[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def eventos_do_movimento(m: dict[str, Any], polo: str) -> list[Evento]:
    cod = m.get("codigo")
    nome = normalizar(m.get("nome"))
    comps = _comps(m)
    d = _data(m)
    if d is None:
        return []
    rot = f"{cod} {m.get('nome')}" + (f" ({', '.join(comps)})" if comps else "")
    ev: list[Evento] = []

    def add(n: str, conf: str = "alta") -> None:
        ev.append(Evento(n, d, rot, conf))

    # Mandados e AR
    if cod == 106:
        if any("nao entregue" in c for c in comps):
            add("citacao_negativa", "media")
        elif any("entregue ao destinatario" in c for c in comps):
            add("mandado_citacao_positivo", "media")
    if cod == 581 and any("aviso de recebimento" in c for c in comps):
        add("ar_positivo", "media")
    # Audiências (12740 conciliação, 12749 instrução, 970/12624 genéricas)
    if cod in (12740, 12749, 970, 12624, 12752):
        tipo = "instrucao" if cod == 12749 else "conciliacao"
        if any("designada" in c or "redesignada" in c for c in comps):
            add(f"audiencia_{tipo}_designada")
        if any(c.endswith("realizada") and "nao" not in c for c in comps):
            add(f"audiencia_{tipo}_realizada")
    # Petições da outra parte (pela natureza; o DataJud não diz quem peticionou)
    if cod == 85:
        if polo == "autor" and any("contestacao" in c for c in comps):
            add("contestacao_juntada", "media")
        if polo == "autor" and any(
            re.search(r"embargos\s*a\s*execucao|^embargos$", c) for c in comps
        ):
            add("intimacao_resposta_embargos_execucao", "media")
        if any("pre executividade" in c or "pre-executividade" in c or "praca" in c for c in comps):
            add("excecao_pre_executividade_apresentada", "media")
        if any(
            re.search(r"recurso (ordinario|inominado)|apelacao|contra razoes", c) for c in comps
        ):
            add("recurso_juntado", "media")  # conciliar decide se foi nosso ou adverso
        if any("agravo" in c for c in comps):
            add("agravo_interno_adverso", "media")
        if any("impugnacao" in c for c in comps):
            add("despacho_manifestacao", "media")
    # Sentenças conforme o polo
    if cod in SENT_PROCEDENCIA:
        if polo in ("reu", "embargado"):
            add("sentenca_desfavoravel")
        else:
            add("sentenca_favoravel")
    if cod in SENT_IMPROCEDENCIA:
        if polo == "autor":
            add("sentenca_desfavoravel")
        else:
            add("sentenca_favoravel")
    if cod in SENT_TERMINATIVA_CONTRA_AUTOR and polo == "autor":
        add("sentenca_desfavoravel")
    if cod in EXTINCAO_PAGAMENTO:
        add("sentenca_extincao_pagamento")
    if cod in EXTINCAO_ACORDO:
        add("sentenca_extincao_acordo")
    if cod in EXTINCAO_DESISTENCIA:
        add("sentenca_extincao_desistencia")
    if cod in (198, 200, 871, 15164):  # embargos de declaração julgados → reabre prazo recursal
        add("decisao_embargos_declaracao_julgados")
    if cod in ACORDAO_DESFAVORAVEL_AO_RECORRENTE:
        add("acordao_proferido", "media")
    if cod == 417:
        add("inclusao_em_pauta")
    if cod == 334:
        add("pedido_gratuidade_devedor_com_indicio_de_capacidade", "media")
    if cod == 268:
        add("obito_parte")
    if cod == 1051:
        add("decurso_de_prazo", "media")
    if cod in DECISAO_A_CUMPRIR:
        add("despacho_manifestacao", "media")
    if cod in (893, 849, 12066):
        add("processo_reativado")
    if cod in ARQUIVO_PROVISORIO:
        add("arquivamento_provisorio")
    if cod in ARQUIVO_DEFINITIVO:
        add("arquivamento_definitivo")
    if cod in (581, 60) and any(c == "alvara" for c in comps):
        add("alvara_expedido")
    if cod == 276:
        add("execucao_frustrada")
    if "penhora" in nome or any("penhora" in c for c in comps):
        add("termo_ou_auto_de_penhora", "media")
    return ev


# Evento → (ato, observação). Eventos sem ato direto viram alertas operacionais.
EVENTO_PARA_ATO: dict[str, tuple[str, str]] = {
    "citacao_negativa": ("peticao_interlocutoria", "pesquisa de endereço / hora certa / edital"),
    "mandado_citacao_positivo": ("citacao_efetivada", "confirmar se o mandado era de citação"),
    "ar_positivo": ("citacao_efetivada", "confirmar AR positivo de citação"),
    "audiencia_conciliacao_realizada": ("audiencia_conciliacao", "audiência realizada"),
    "audiencia_instrucao_realizada": ("audiencia_instrucao", "audiência realizada"),
    "contestacao_juntada": ("replica", "contestação na monitória/conhecimento"),
    "intimacao_resposta_embargos_execucao": ("impugnacao_embargos_execucao", "embargos opostos"),
    "excecao_pre_executividade_apresentada": ("excecao_pre_executividade", "responder à exceção"),
    "agravo_interno_adverso": ("resposta_agravo_interno", "confirmar se o agravo é adverso"),
    "sentenca_desfavoravel": ("apelacao", "sentença contra o Banco"),
    "decisao_embargos_declaracao_julgados": ("apelacao", "prazo recursal reaberto"),
    "inclusao_em_pauta": ("memoriais", "e avaliar sustentação oral"),
    "pedido_gratuidade_devedor_com_indicio_de_capacidade": (
        "impugnacao_gratuidade",
        "só se houver indício de capacidade",
    ),
    "obito_parte": ("habilitacao_credito", "inventário / sucessão do devedor"),
    "sentenca_extincao_pagamento": ("extincao_1grau", "extinção por pagamento"),
    "sentenca_extincao_acordo": ("extincao_1grau", "extinção por acordo"),
    "sentenca_extincao_desistencia": ("extincao_1grau", "extinção por desistência"),
    "decurso_de_prazo": ("peticao_interlocutoria", "prazo vencido: pedir constrição/prosseguir"),
    "despacho_manifestacao": ("peticao_interlocutoria", "decisão/despacho a cumprir"),
    "processo_reativado": ("peticao_interlocutoria", "processo reativado: requerer prosseguimento"),
    "execucao_frustrada": ("peticao_interlocutoria", "pesquisa de bens / suspensão 921"),
    "termo_ou_auto_de_penhora": ("arresto_penhora", "confirmar penhora efetivada"),
}
ALERTAS = {
    "audiencia_conciliacao_designada": "audiência designada: preparar e avisar o banco",
    "audiencia_instrucao_designada": "audiência designada: preparar e avisar o banco",
    "arquivamento_definitivo": "processo baixado no tribunal; conferir a ficha no Benner",
    "arquivamento_provisorio": "arquivo provisório: controlar prescrição intercorrente",
    "alvara_expedido": "alvará expedido: levantar e repassar ao banco no mesmo dia (cl. 12, a)",
    "sentenca_favoravel": "sentença favorável: acompanhar recurso adverso (contrarrazões R$ 200)",
    "acordao_proferido": "acórdão: avaliar embargos de declaração / recurso / cumprimento",
    "recurso_juntado": "recurso juntado: se adverso, contrarrazões (R$ 200)",
}

DIAS_PARA_ATENDER = 45  # janela para considerar o ato atendido após o evento
SEM_MOVIMENTO_DIAS = 90


@dataclass
class Oportunidade:
    cnj: str
    evento: str
    data_evento: date
    ato_id: str | None
    valor: float | None
    papel: str | None
    prazo: date | None
    confianca: str
    movimento: str
    observacao: str
    status: str = "ABERTA"  # ABERTA | ATENDIDA | PERDIDA | ALERTA
    atendida_por: str | None = None


@dataclass
class Processo:
    cnj: str
    classe: str
    tribunal: str
    movimentos: list[dict[str, Any]] = field(default_factory=list)
    ultima_movimentacao: date | None = None


def unir_graus(docs: Iterable[dict[str, Any]]) -> dict[str, Processo]:
    """O DataJud devolve um documento por grau; junta os movimentos por número."""
    out: dict[str, Processo] = {}
    for s in docs:
        n = s["numeroProcesso"]
        p = out.get(n)
        classe = (s.get("classe") or {}).get("nome") or ""
        if p is None:
            p = out[n] = Processo(n, classe, s.get("tribunal") or "")
        elif s.get("grau") in ("G1", "JE") and classe:
            p.classe = classe
        p.movimentos.extend(s.get("movimentos") or [])
    for p in out.values():
        datas = [d for d in (_data(m) for m in p.movimentos) if d]
        p.ultima_movimentacao = max(datas) if datas else None
    return out


def detectar(p: Processo, hoje: date, desde: date | None = None) -> list[Oportunidade]:
    gat = carregar_gatilhos()
    tab = carregar_tabela()
    polo = polo_do_banco(p.classe)
    coluna = enquadrar_coluna(p.classe, None, p.cnj)
    vistos: set[tuple[str, date]] = set()
    ops: list[Oportunidade] = []
    for m in sorted(p.movimentos, key=lambda x: x.get("dataHora") or ""):
        for ev in eventos_do_movimento(m, polo):
            if desde and ev.data < desde:
                continue
            if (ev.nome, ev.data) in vistos:
                continue
            vistos.add((ev.nome, ev.data))
            if ev.nome in EVENTO_PARA_ATO:
                ato_id, obs = EVENTO_PARA_ATO[ev.nome]
                g = gat.get(ato_id)
                ato = tab.atos.get(ato_id)
                valor = ato.valor(coluna) if ato else None
                if ato and valor is None:
                    valor = ato.valor("demais") or ato.valor("rec_cred")
                prazo = (
                    ev.data + timedelta(days=int(g.prazo_dias * 1.4))
                    if g and g.prazo_dias
                    else None
                )
                ops.append(
                    Oportunidade(
                        p.cnj,
                        ev.nome,
                        ev.data,
                        ato_id,
                        valor,
                        g.papel if g else None,
                        prazo,
                        ev.confianca,
                        ev.movimento,
                        obs,
                    )
                )
            elif ev.nome in ALERTAS:
                ops.append(
                    Oportunidade(
                        p.cnj,
                        ev.nome,
                        ev.data,
                        None,
                        None,
                        None,
                        None,
                        ev.confianca,
                        ev.movimento,
                        ALERTAS[ev.nome],
                        status="ALERTA",
                    )
                )
    if p.ultima_movimentacao and (hoje - p.ultima_movimentacao).days > SEM_MOVIMENTO_DIAS:
        ato = tab.atos["peticao_interlocutoria"]
        ops.append(
            Oportunidade(
                p.cnj,
                "processo_sem_evento_90_dias",
                p.ultima_movimentacao,
                "peticao_interlocutoria",
                ato.valor(coluna) or 120.0,
                "redige",
                hoje,
                "alta",
                "—",
                f"sem movimento desde {p.ultima_movimentacao:%d/%m/%Y}",
            )
        )
    return ops


# Atos cobrados que atendem cada ato da oportunidade (equivalências).
_ATENDE: dict[str, set[str]] = {
    "peticao_interlocutoria": {"peticao_interlocutoria", "juntada_planilha_custas"},
    "apelacao": {"apelacao", "embargos_declaracao", "agravo_instrumento"},
    "memoriais": {"memoriais", "sustentacao_oral"},
}


def conciliar(
    ops: list[Oportunidade],
    cobrados: dict[str, list[tuple[date, str]]],
    hoje: date,
) -> None:
    """`cobrados`: dígitos do CNJ → [(data do protocolo, ato_id)] das prestações de contas."""
    for o in ops:
        if o.status == "ALERTA" or o.ato_id is None:
            continue
        aceitos = _ATENDE.get(o.ato_id, {o.ato_id})
        limite = o.data_evento + timedelta(days=DIAS_PARA_ATENDER)
        for d, ato in cobrados.get(o.cnj, []):
            if ato in aceitos and o.data_evento - timedelta(days=3) <= d <= limite:
                o.status, o.atendida_por = "ATENDIDA", f"{ato} em {d:%d/%m/%Y}"
                break
        else:
            if (o.prazo and o.prazo < hoje) or (not o.prazo and limite < hoje):
                o.status = "PERDIDA"
