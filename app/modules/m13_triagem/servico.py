"""Triagem em produção: ingestão da caixa basa@, papéis → pessoas e o resumo por pessoa.

Nada aqui envia, move ou altera e-mails: o resultado é o painel /painel/triagem, onde cada
pessoa vê só o que é dela e marca como visto/resolvido.
"""

from __future__ import annotations

import re
import uuid
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.faturamento import BasaFicha
from app.models.triagem import TriagemEmail, TriagemPapel
from app.modules.m13_triagem.classificar import Email, classificar

PAPEIS_PADRAO: dict[str, str] = {
    "coordenacao": "Coordenação do contrato BASA (relação com CCONS/GEJUR, Benner, reuniões)",
    "financeiro": "Prestação de contas, NF e recebimento",
    "equipe_pa": "Advogados das fichas do Pará",
    "equipe_am": "Advogados das fichas do Amazonas",
    "prazos_pa": "Controle de prazos / intimações do Pará",
    "prazos_am": "Controle de prazos / intimações do Amazonas",
    "prazos_escritorio": "Prazos de outros clientes (intimações fora do contrato BASA)",
}
_URG = {"alta": 0, "media": 1, "baixa": 2}


def _texto_limpo(t: str, n: int = 600) -> str:
    t = re.sub(r"<[^>]+>", " ", t or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n]


def garantir_papeis(db: Session, tenant_id: uuid.UUID) -> None:
    existentes = set(db.scalars(select(TriagemPapel.papel)))
    for p, d in PAPEIS_PADRAO.items():
        if p not in existentes:
            db.add(TriagemPapel(tenant_id=tenant_id, papel=p, descricao=d, pessoas=[]))
    db.commit()


def ingerir(
    db: Session, tenant_id: uuid.UUID, emails: Iterable[Email], caixa: str
) -> dict[str, int]:
    """Classifica e grava os e-mails novos; reprocessar o mesmo id não duplica."""
    garantir_papeis(db, tenant_id)
    ja = set(db.scalars(select(TriagemEmail.mensagem_id).where(TriagemEmail.caixa == caixa)))
    fichas = _fichas(db)
    carteira = set(fichas)
    c: Counter[str] = Counter()
    for e in emails:
        if e.id in ja:
            c["repetidos"] += 1
            continue
        tr = classificar(e, carteira=carteira)
        rec = None
        if e.recebido_em:
            try:
                rec = datetime.fromisoformat(e.recebido_em.replace("Z", "+00:00"))
            except ValueError:
                rec = None
        db.add(
            TriagemEmail(
                tenant_id=tenant_id,
                mensagem_id=e.id[:400],
                caixa=caixa[:200],
                recebido_em=rec,
                remetente=e.remetente[:200],
                assunto=(e.assunto or "")[:500],
                trecho=_texto_limpo(e.corpo),
                texto_integral=_texto_limpo(e.corpo, 30000) if caixa == "djen" else None,
                link=e.link,
                conversa=(e.conversa or None) and e.conversa[:400],
                categoria=tr.categoria,
                urgencia=tr.urgencia,
                papeis=tr.papeis,
                cnjs=tr.cnjs,
                fichas=[x for d in tr.cnjs for x in fichas.get(d, [])],
                uf=tr.uf,
                motivo=tr.motivo,
                acao=tr.acao,
                internos_copiados=tr.internos_copiados,
                internos_necessarios=tr.internos_necessarios,
                status="resolvido" if tr.categoria == "IGNORAR" else "pendente",
            )
        )
        ja.add(e.id)
        c["novos"] += 1
        c[tr.categoria] += 1
    db.commit()
    return dict(c)


def _fichas(db: Session) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for f in db.scalars(select(BasaFicha)):
        out.setdefault(f.cnj, []).append(f.ficha)
    return out


def reclassificar(db: Session) -> dict[str, int]:
    """Reaplica as regras atuais aos e-mails gravados (com o trecho guardado); não mexe no
    status já marcado pela equipe, exceto o que passar a ser ruído."""
    fichas = _fichas(db)
    carteira = set(fichas)
    c: Counter[str] = Counter()
    for t in db.scalars(select(TriagemEmail)):
        tr = classificar(
            Email(id=t.mensagem_id, remetente=t.remetente, assunto=t.assunto, corpo=t.trecho or ""),
            carteira=carteira,
        )
        if (tr.categoria, tr.papeis, tr.acao) != (t.categoria, t.papeis, t.acao):
            c["alterados"] += 1
        t.categoria, t.urgencia, t.papeis, t.acao, t.motivo = (
            tr.categoria,
            tr.urgencia,
            tr.papeis,
            tr.acao,
            tr.motivo,
        )
        t.cnjs, t.uf = tr.cnjs, tr.uf
        t.fichas = [x for d in tr.cnjs for x in fichas.get(d, [])]
        t.internos_necessarios = tr.internos_necessarios
        c["total"] += 1
    db.commit()
    return dict(c)


def ultimo_recebido(db: Session, caixa: str) -> datetime | None:
    return db.scalar(select(func.max(TriagemEmail.recebido_em)).where(TriagemEmail.caixa == caixa))


def sincronizar_caixa(
    db: Session, tenant_id: uuid.UUID, client: Any, caixa: str, dias_iniciais: int = 30
) -> dict[str, int]:
    desde = ultimo_recebido(db, caixa)
    if desde is None:
        desde = datetime.now(UTC) - timedelta(days=dias_iniciais)
    else:
        if desde.tzinfo is None:
            desde = desde.replace(tzinfo=UTC)
        desde -= timedelta(minutes=5)
    return ingerir(db, tenant_id, client.mensagens(caixa, desde), caixa)


def papeis(db: Session) -> list[dict[str, Any]]:
    return [
        {"papel": p.papel, "descricao": p.descricao, "pessoas": p.pessoas or []}
        for p in db.scalars(select(TriagemPapel).order_by(TriagemPapel.papel))
    ]


def definir_papel(
    db: Session, tenant_id: uuid.UUID, papel: str, pessoas: list[dict[str, str]]
) -> dict[str, Any]:
    p = db.scalar(select(TriagemPapel).where(TriagemPapel.papel == papel))
    if p is None:
        p = TriagemPapel(tenant_id=tenant_id, papel=papel[:40], pessoas=[])
        db.add(p)
    p.pessoas = [
        {"nome": str(x.get("nome", ""))[:80], "email": str(x.get("email", "")).lower()[:120]}
        for x in pessoas
        if x.get("email") or x.get("nome")
    ]
    db.commit()
    return {"papel": p.papel, "descricao": p.descricao, "pessoas": p.pessoas}


def _item(t: TriagemEmail) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "recebido_em": t.recebido_em.isoformat() if t.recebido_em else None,
        "remetente": t.remetente,
        "assunto": t.assunto,
        "trecho": t.trecho,
        "link": t.link,
        "categoria": t.categoria,
        "urgencia": t.urgencia,
        "papeis": t.papeis,
        "processos": t.cnjs,
        "fichas": t.fichas,
        "uf": t.uf,
        "acao": t.acao,
        "copiados": t.internos_copiados,
        "necessarios": t.internos_necessarios,
        "status": t.status,
        "tratado_por": t.tratado_por,
    }


def resumo(
    db: Session, pessoa: str | None = None, status: str | None = "pendente", dias: int = 30
) -> dict[str, Any]:
    """Itens por papel; com `pessoa` (e-mail), só os papéis dela."""
    corte = datetime.now(UTC) - timedelta(days=dias)
    q = select(TriagemEmail).where(
        (TriagemEmail.recebido_em >= corte) | (TriagemEmail.recebido_em.is_(None))
    )
    if status:
        q = q.where(TriagemEmail.status == status)
    itens = [t for t in db.scalars(q) if t.categoria != "IGNORAR" or status == "resolvido"]
    tabela = {p["papel"]: p for p in papeis(db)}
    meus: set[str] | None = None
    if pessoa:
        pe = pessoa.lower()
        meus = {k for k, p in tabela.items() if any(x.get("email") == pe for x in p["pessoas"])}
    por_papel: dict[str, list[dict[str, Any]]] = {}
    for t in itens:
        for papel in t.papeis or ["coordenacao"]:
            if meus is not None and papel not in meus:
                continue
            por_papel.setdefault(papel, []).append(_item(t))
    for v in por_papel.values():
        v.sort(key=lambda x: (_URG.get(x["urgencia"], 9), x["recebido_em"] or ""))
    todos = list(db.scalars(select(TriagemEmail).where(TriagemEmail.recebido_em >= corte)))
    uteis = [t for t in todos if t.categoria != "IGNORAR"]
    return {
        "periodo_dias": dias,
        "papeis": [
            {
                "papel": k,
                "descricao": tabela.get(k, {}).get("descricao"),
                "pessoas": tabela.get(k, {}).get("pessoas", []),
                "itens": v,
            }
            for k, v in sorted(por_papel.items())
        ],
        "metricas": {
            "emails": len(todos),
            "ignorados": len(todos) - len(uteis),
            "pendentes": sum(1 for t in uteis if t.status == "pendente"),
            "urgentes_pendentes": sum(
                1 for t in uteis if t.status == "pendente" and t.urgencia == "alta"
            ),
            "copias_internas": sum(t.internos_copiados for t in uteis),
            "copias_necessarias": sum(
                min(t.internos_necessarios, t.internos_copiados) for t in uteis
            ),
            "por_categoria": dict(Counter(t.categoria for t in todos)),
        },
    }


def marcar(db: Session, tid: uuid.UUID, status: str, por: str) -> dict[str, Any]:
    if status not in ("pendente", "visto", "resolvido"):
        raise ValueError("status inválido")
    t = db.get(TriagemEmail, tid)
    if t is None:
        raise KeyError(tid)
    t.status = status
    t.tratado_por = por[:80]
    t.tratado_em = datetime.now(UTC)
    db.commit()
    return _item(t)


# --- intimações do DJEN (Comunica PJe) -----------------------------------------------------


def sincronizar_intimacoes(
    db: Session,
    tenant_id: uuid.UUID,
    provider: Any,
    desde: Any,
    oabs: list[str],
    nome_parte: str | None,
) -> dict[str, int]:
    """Busca no DJEN e manda para a triagem. A API do DJEN recusa IP de fora do Brasil (403):
    em produção quem busca é o relay no Mac do escritório (scripts/djen_relay.py), que chama
    `importar_intimacoes`; esta função fica para rodar de dentro do Brasil."""
    por_parte = list(provider.fetch(since=desde, nome_parte=nome_parte)) if nome_parte else []
    por_oab = [r for oab in oabs for r in provider.fetch(since=desde, oab=oab)]
    return importar_intimacoes(db, tenant_id, por_parte, por_oab)


def importar_intimacoes(
    db: Session, tenant_id: uuid.UUID, por_parte: list[Any], por_oab: list[Any]
) -> dict[str, int]:
    """Comunicações do DJEN → triagem (caixa 'djen'). As buscadas pelo nome do Banco só entram
    se o processo é da carteira; as das OABs do escritório entram todas."""
    carteira = set(_fichas(db))
    vistos: dict[str, Any] = {}
    st: Counter[str] = Counter()
    for r in por_parte:
        st["djen_parte"] += 1
        if r.cnj_number and r.cnj_number in carteira:
            vistos[r.provider_ref] = r
    for r in por_oab:
        st["djen_oab"] += 1
        vistos[r.provider_ref] = r
    emails = []
    for r in vistos.values():
        raw = r.raw or {}
        tipo = raw.get("tipoComunicacao") or "Comunicação"
        classe = raw.get("nomeClasse") or ""
        orgao = raw.get("nomeOrgao") or ""
        num = r.cnj_number or ""
        cab = (
            f"PROCESSO Nº {num[:7]}-{num[7:9]}.{num[9:13]}.{num[13:14]}.{num[14:16]}.{num[16:]}"
            if len(num) == 20
            else ""
        )
        emails.append(
            Email(
                id=f"djen:{r.provider_ref}",
                remetente="djen@comunica.pje.jus.br",
                assunto=f"DJEN — {tipo} — {r.court or ''} — {classe}".strip(" —"),
                corpo=f"{cab}\n{orgao}\n{r.text}",
                recebido_em=r.published_at.isoformat() + "Z" if r.published_at else "",
                link=raw.get("link"),
            )
        )
    res = ingerir(db, tenant_id, emails, "djen")
    return {**dict(st), **{f"triagem_{k}": v for k, v in res.items()}}
