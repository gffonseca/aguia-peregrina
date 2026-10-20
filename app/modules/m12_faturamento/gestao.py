"""Painel gerencial do contrato BASA: números de todas as frentes num só lugar."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.benner import BennerCorrecao, BennerDocumento
from app.models.faturamento import (
    BasaAtoCobrado,
    BasaFicha,
    BasaRecebivel,
    MotorExecucao,
    OportunidadeDecisao,
)
from app.models.triagem import TriagemEmail
from app.modules.m12_faturamento import recebiveis as rcb
from app.modules.m12_faturamento.fila import fila

ATIVAS = {"em andamento", "em encerramento", "em reativacao"}


def resumo(db: Session, hoje: date | None = None) -> dict[str, Any]:
    from app.modules.m12_faturamento.servico import _rec
    from app.modules.m12_faturamento.tabela import normalizar

    hoje = hoje or date.today()
    fichas = list(db.scalars(select(BasaFicha)))
    ativas = [f for f in fichas if normalizar(f.situacao) in ATIVAS]

    # faturamento por mês e cobertura (processos distintos com ato cobrado / carteira ativa)
    meses: dict[str, dict[str, Any]] = defaultdict(lambda: {"atos": 0, "valor": 0.0, "proc": set()})
    for a in db.scalars(select(BasaAtoCobrado)):
        m = meses[a.competencia]
        m["atos"] += 1
        m["valor"] += a.valor or 0
        m["proc"].add(a.cnj)
    faturamento = [
        {
            "competencia": k,
            "atos": v["atos"],
            "valor": round(v["valor"], 2),
            "processos": len(v["proc"]),
            "cobertura": round(len(v["proc"]) / len(ativas), 4) if ativas else None,
        }
        for k, v in sorted(meses.items())
    ]

    recs = list(db.scalars(select(BasaRecebivel)))
    sit = [rcb.situacao(_rec(r), hoje) for r in recs]
    em_aberto = sum(s.em_aberto for s in sit)
    vencido = sum(s.em_aberto for s in sit if any(a.codigo == "VENCIDO" for a in s.alertas))

    ult = db.scalar(
        select(MotorExecucao)
        .where(MotorExecucao.status == "ok")
        .order_by(MotorExecucao.iniciado_em.desc())
    )
    g = fila(db, tipo="gatilhos", limite=1, hoje=hoje)

    corte = datetime.now(UTC) - timedelta(days=30)
    decs = [d for d in db.scalars(select(OportunidadeDecisao)) if d.em and _aware(d.em) >= corte]
    por_pessoa: dict[str, Counter[str]] = defaultdict(Counter)
    for d in decs:
        por_pessoa[d.por][d.decisao] += 1

    corr = Counter((c.tipo, c.status) for c in db.scalars(select(BennerCorrecao)))
    tri = [t for t in db.scalars(select(TriagemEmail)) if t.categoria != "IGNORAR"]
    ult_doc = max((d.data for d in db.scalars(select(BennerDocumento)) if d.data), default=None)

    return {
        "hoje": hoje.isoformat(),
        "carteira": {"fichas": len(fichas), "ativas": len(ativas)},
        "faturamento": faturamento,
        "recebiveis": {
            "em_aberto": round(em_aberto, 2),
            "vencido": round(vencido, 2),
            "prestacoes": len(recs),
            "pagas": sum(1 for s in sit if s.etapa == "PAGA"),
        },
        "motor": {
            "ultima_rodada": ult.iniciado_em.isoformat() if ult else None,
            "processos": (ult.estatisticas or {}).get("processos") if ult else None,
            "perdidas": (ult.estatisticas or {}).get("perdidas") if ult else None,
            "valor_perdido": (ult.estatisticas or {}).get("valor_perdido") if ult else None,
            "no_prazo": g["no_prazo"],
            "no_prazo_alta": g["no_prazo_alta"],
            "valor_no_prazo": g["valor_no_prazo"],
            "prazo_passou": g["prazo_passou"],
        },
        "produtividade_30d": {
            p: {"feito": c["feito"], "nao_cabe": c["nao_cabe"], "em_andamento": c["em_andamento"]}
            for p, c in sorted(por_pessoa.items(), key=lambda kv: -kv[1]["feito"])
        },
        "correcoes_benner": {
            "pendentes": sum(v for (t, s), v in corr.items() if s == "pendente"),
            "feitas": sum(v for (t, s), v in corr.items() if s == "feito"),
            "confirmadas": sum(v for (t, s), v in corr.items() if s == "confirmado"),
            "por_tipo_pendente": {t: v for (t, s), v in corr.items() if s == "pendente"},
        },
        "triagem": {
            "pendentes": sum(1 for t in tri if t.status == "pendente"),
            "urgentes": sum(1 for t in tri if t.status == "pendente" and t.urgencia == "alta"),
            "copias_internas": sum(t.internos_copiados for t in tri),
            "copias_necessarias": sum(
                min(t.internos_necessarios, t.internos_copiados) for t in tri
            ),
        },
        "benner_documentos_ate": ult_doc.isoformat() if ult_doc else None,
    }


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=UTC)
