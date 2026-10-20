"""Fila de atos cobráveis por pessoa, a partir da última rodada do motor.

Três filas, nesta ordem de prioridade:
- "gatilhos": evento no processo que pede um ato da tabela (sentença contra o Banco →
  apelação, embargos julgados, audiência realizada, pauta, óbito...);
- "alertas": acontecimentos que pedem atenção e costumam virar ato (recurso adverso →
  contrarrazões, alvará, audiência designada, acórdão);
- "parados": processos sem movimento há 90+ dias (petição para impulsionar). São milhares;
  a fila entrega um lote por dia por pessoa, dos mais antigos para os mais novos. Cuidado do
  contrato: reiteração de pedido anterior não é remunerada — a petição tem de pedir algo novo.

A pessoa vê só a UF dos papéis dela (equipe_pa / equipe_am, os mesmos da triagem). O que ela
decide (feito / não cabe / em andamento) fica em `motor_decisoes` e o motor respeita nas
rodadas seguintes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.faturamento import MotorOportunidade, OportunidadeDecisao
from app.models.triagem import TriagemPapel
from app.modules.m13_triagem.classificar import uf_do_cnj

PARADOS = "processo_sem_evento_90_dias"
ALERTAS_DE_FILA = {
    "recurso_juntado",
    "sentenca_favoravel",
    "acordao_proferido",
    "alvara_expedido",
    "audiencia_conciliacao_designada",
    "audiencia_instrucao_designada",
}
ROTULO = {
    "sentenca_desfavoravel": "Sentença contra o Banco",
    "decisao_embargos_declaracao_julgados": "Embargos de declaração julgados",
    "audiencia_conciliacao_realizada": "Audiência de conciliação realizada",
    "audiencia_instrucao_realizada": "Audiência de instrução realizada",
    "inclusao_em_pauta": "Processo incluído em pauta",
    "obito_parte": "Óbito de parte",
    "citacao_negativa": "Citação negativa",
    "mandado_citacao_positivo": "Mandado de citação positivo",
    "ar_positivo": "AR positivo",
    "contestacao_juntada": "Contestação juntada",
    "intimacao_resposta_embargos_execucao": "Embargos à execução opostos",
    "excecao_pre_executividade_apresentada": "Exceção de pré-executividade",
    "agravo_interno_adverso": "Agravo interno",
    "decurso_de_prazo": "Decurso de prazo",
    "despacho_manifestacao": "Despacho/decisão a cumprir",
    "processo_reativado": "Processo reativado",
    "execucao_frustrada": "Execução frustrada",
    "termo_ou_auto_de_penhora": "Penhora",
    "sentenca_extincao_pagamento": "Extinção por pagamento",
    "sentenca_extincao_acordo": "Extinção por acordo",
    "sentenca_extincao_desistencia": "Extinção por desistência",
    "recurso_juntado": "Recurso juntado",
    "sentenca_favoravel": "Sentença favorável",
    "acordao_proferido": "Acórdão proferido",
    "alvara_expedido": "Alvará expedido",
    "audiencia_conciliacao_designada": "Audiência de conciliação designada",
    "audiencia_instrucao_designada": "Audiência de instrução designada",
    PARADOS: "Sem movimento há 90+ dias",
}
ATO = {
    "apelacao": "Apelação",
    "memoriais": "Memoriais",
    "audiencia_conciliacao": "Audiência de conciliação",
    "audiencia_instrucao": "Audiência de instrução",
    "habilitacao_credito": "Habilitação",
    "peticao_interlocutoria": "Petição interlocutória",
    "citacao_efetivada": "Citação efetivada",
    "replica": "Réplica",
    "impugnacao_embargos_execucao": "Impugnação aos embargos",
    "excecao_pre_executividade": "Resposta à exceção",
    "resposta_agravo_interno": "Resposta a agravo interno",
    "arresto_penhora": "Penhora",
    "extincao_1grau": "Extinção (resultado)",
    "impugnacao_gratuidade": "Impugnação à gratuidade",
}
DECISOES = ("feito", "nao_cabe", "em_andamento")


def chave(cnj: str, evento: str, data_evento: date) -> tuple[str, str, date]:
    return (cnj, evento, data_evento)


def decisoes(db: Session) -> dict[tuple[str, str, date], OportunidadeDecisao]:
    return {
        chave(d.cnj, d.evento, d.data_evento): d for d in db.scalars(select(OportunidadeDecisao))
    }


def _ufs_da_pessoa(db: Session, pessoa: str | None) -> set[str] | None:
    """None = sem filtro (coordenação/tudo)."""
    if not pessoa:
        return None
    pe = pessoa.lower()
    ufs: set[str] = set()
    for p in db.scalars(select(TriagemPapel)):
        if any((x.get("email") or "").lower() == pe for x in p.pessoas or []):
            if p.papel in ("equipe_pa", "prazos_pa"):
                ufs.add("PA")
            elif p.papel in ("equipe_am", "prazos_am"):
                ufs.add("AM")
            elif p.papel == "coordenacao":
                return None
    return ufs


def _item(o: MotorOportunidade, d: OportunidadeDecisao | None, hoje: date) -> dict[str, Any]:
    return {
        "processo": o.cnj,
        "ficha": o.ficha,
        "uf": uf_do_cnj(o.cnj),
        "evento": o.evento,
        "evento_rotulo": ROTULO.get(o.evento, o.evento.replace("_", " ")),
        "data_evento": o.data_evento.isoformat(),
        "ato": o.ato_id,
        "ato_rotulo": ATO.get(o.ato_id or "", o.ato_id),
        "valor": o.valor,
        "prazo": o.prazo.isoformat() if o.prazo else None,
        "prazo_passou": bool(o.prazo and o.prazo < hoje and o.evento != PARADOS),
        "confianca": o.confianca,
        "status": o.status,
        "movimento": o.movimento,
        "observacao": o.observacao,
        "decisao": d.decisao if d else None,
        "decisao_por": d.por if d else None,
        "decisao_obs": d.observacao if d else None,
    }


def fila(
    db: Session,
    pessoa: str | None = None,
    tipo: str = "gatilhos",
    limite: int = 50,
    incluir_decididas: bool = False,
    hoje: date | None = None,
) -> dict[str, Any]:
    hoje = hoje or date.today()
    ufs = _ufs_da_pessoa(db, pessoa)
    dec = decisoes(db)
    q = select(MotorOportunidade)
    if tipo == "gatilhos":
        q = q.where(MotorOportunidade.status == "ABERTA", MotorOportunidade.evento != PARADOS)
    elif tipo == "alertas":
        q = q.where(
            MotorOportunidade.status == "ALERTA",
            MotorOportunidade.evento.in_(sorted(ALERTAS_DE_FILA)),
        )
    elif tipo == "parados":
        q = q.where(MotorOportunidade.evento == PARADOS)
    else:
        raise ValueError("tipo inválido")
    itens = []
    for o in db.scalars(q):
        if ufs is not None and uf_do_cnj(o.cnj) not in ufs:
            continue
        d = dec.get(chave(o.cnj, o.evento, o.data_evento))
        if d and d.decisao in ("feito", "nao_cabe") and not incluir_decididas:
            continue
        itens.append(_item(o, d, hoje))
    if tipo == "parados":
        itens.sort(key=lambda x: x["data_evento"])  # parado há mais tempo primeiro
    else:
        itens.sort(key=lambda x: (x["prazo"] or "9999", -(x["valor"] or 0)))
    total, valor = len(itens), sum(x["valor"] or 0 for x in itens)
    return {
        "tipo": tipo,
        "ufs": sorted(ufs) if ufs is not None else None,
        "total": total,
        "valor_total": round(valor, 2),
        "itens": itens[:limite],
    }


def decidir(
    db: Session,
    tenant_id: uuid.UUID,
    cnj: str,
    evento: str,
    data_evento: date,
    decisao: str | None,
    por: str,
    observacao: str | None = None,
) -> dict[str, Any]:
    """Grava (ou apaga, com decisao=None) a decisão; vale para as rodadas seguintes."""
    k = chave(cnj, evento, data_evento)
    d = decisoes(db).get(k)
    if decisao is None:
        if d is not None:
            db.delete(d)
            db.commit()
        return {"processo": cnj, "evento": evento, "decisao": None}
    if decisao not in DECISOES:
        raise ValueError("decisão inválida")
    if d is None:
        d = OportunidadeDecisao(
            tenant_id=tenant_id, cnj=cnj, evento=evento, data_evento=data_evento
        )
        db.add(d)
    d.decisao, d.por, d.em = decisao, por[:80], datetime.now(UTC)
    d.observacao = (observacao or None) and observacao[:2000]
    db.commit()
    return {"processo": cnj, "evento": evento, "decisao": decisao, "por": d.por}


def aplicar_decisoes(db: Session, ops: list[Any]) -> int:
    """Usado pelo motor: 'feito' vira ATENDIDA e 'não cabe' vira DESCARTADA."""
    dec = decisoes(db)
    n = 0
    for o in ops:
        d = dec.get(chave(o.cnj, o.evento, o.data_evento))
        if d is None or d.decisao == "em_andamento":
            continue
        if d.decisao == "feito":
            o.status, o.atendida_por = "ATENDIDA", f"equipe: {d.por}"
        else:
            o.status, o.atendida_por = "DESCARTADA", f"não cabe: {d.por}"
        n += 1
    return n
