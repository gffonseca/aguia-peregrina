"""Fila de correções no Benner (M14).

Quatro tipos, cada um com a evidência que justifica a correção:
- SITUACAO: ficha "Em andamento" no Benner, mas o último movimento no tribunal (DataJud) é a
  baixa/arquivamento definitivo → propor "Encerrado".
- NUMERO_PROCESSO: número do processo da ficha inválido (dígito verificador) ou que o DataJud
  não encontra no tribunal → conferir e corrigir o número.
- FICHA_INEXISTENTE: ficha citada numa prestação que não existe no Benner (e cujo processo
  também não está em outra ficha) → pedir o cadastro à CCONS ou corrigir a prestação.
- SUBIR_PECA: ato cobrado sem a peça no Benner (vem do conferente) → subir o documento.

Ciclo: pendente → feito (pessoa ou robô) → confirmado (o export seguinte do Benner mostra a
correção) | nao_procede (com motivo). Regerar a fila não duplica nem reabre o que a equipe já
tratou; só atualiza a evidência do que segue pendente.
"""

from __future__ import annotations

import re
import uuid
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import cnj as cnjlib
from app.integrations.datajud.client import alias_do_tribunal
from app.models.benner import BennerCorrecao
from app.models.faturamento import BasaAtoCobrado, BasaFicha, DataJudProcesso
from app.modules.m12_faturamento.deteccao import ARQUIVO_DEFINITIVO
from app.modules.m12_faturamento.tabela import normalizar

ATIVAS = {"em andamento", "em encerramento", "em reativacao"}
TIPOS = ("SITUACAO", "NUMERO_PROCESSO", "FICHA_INEXISTENTE", "SUBIR_PECA")
STATUS = ("pendente", "feito", "confirmado", "nao_procede", "superado")
BENNER_URL = "https://basa.bennercloud.com.br/JURIDICO/"


def _dig(s: Any) -> str:
    return re.sub(r"\D", "", str(s or ""))


def fmt(d: str | None) -> str:
    d = _dig(d)
    return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13]}.{d[14:16]}.{d[16:]}" if len(d) == 20 else d


def _agora() -> datetime:
    return datetime.now(UTC)


def _upsert(
    db: Session,
    tenant_id: uuid.UUID,
    existentes: dict[str, BennerCorrecao],
    vistos: set[str] | None = None,
    **kw: Any,
) -> str:
    """Cria o item ou atualiza a evidência; devolve 'novo' | 'atualizado' | 'mantido'."""
    chave = kw["chave"][:300]
    if vistos is not None:
        vistos.add(chave)
    c = existentes.get(chave)
    if c is None:
        c = BennerCorrecao(tenant_id=tenant_id, status="pendente", historico=[], **kw)
        c.chave = chave
        db.add(c)
        existentes[chave] = c
        return "novo"
    if c.status == "pendente":
        for k in ("valor_atual", "valor_proposto", "evidencia", "confianca", "origem", "cnj"):
            if k in kw:
                setattr(c, k, kw[k])
        return "atualizado"
    return "mantido"


def _ultimo_arquivamento(p: DataJudProcesso) -> tuple[date, str] | None:
    melhor: tuple[date, str] | None = None
    for g in (p.graus or {}).values():
        for cod, nome, d, _comps in g.get("movimentos") or []:
            if cod in ARQUIVO_DEFINITIVO:
                dt = date.fromisoformat(d[:10])
                if melhor is None or dt > melhor[0]:
                    melhor = (dt, nome)
    return melhor


def gerar(db: Session, tenant_id: uuid.UUID) -> dict[str, int]:
    existentes = {c.chave: c for c in db.scalars(select(BennerCorrecao))}
    fichas = list(db.scalars(select(BasaFicha)))
    por_ficha = {f.ficha: f for f in fichas}
    por_cnj: dict[str, list[BasaFicha]] = defaultdict(list)
    for f in fichas:
        por_cnj[f.cnj].append(f)
    dj = {p.cnj: p for p in db.scalars(select(DataJudProcesso))}
    datajud_rodou = bool(dj)
    st: Counter[str] = Counter()
    vistos: set[str] = set()

    for f in fichas:
        if normalizar(f.situacao) not in ATIVAS:
            continue
        d = _dig(f.cnj)
        p = cnjlib.parse(d) if len(d) == 20 else None
        # número fora do padrão: só aponta se o tribunal também não o reconhece (há processos
        # antigos do TJPA cadastrados no tribunal com dígito verificador que não fecha)
        if (p is None or not p.is_valid) and d not in dj:
            st[
                "NUMERO_PROCESSO:"
                + _upsert(
                    db,
                    tenant_id,
                    existentes,
                    vistos=vistos,
                    tipo="NUMERO_PROCESSO",
                    chave=f"NUMERO_PROCESSO|{f.ficha}|invalido",
                    ficha=f.ficha,
                    cnj=f.cnj,
                    campo="Nº processo principal",
                    valor_atual=f.cnj or "(vazio)",
                    valor_proposto="número CNJ correto (conferir nos autos)",
                    confianca="alta",
                    evidencia=(
                        "dígito verificador não fecha (Res. CNJ 65/2008) e o DataJud não "
                        "encontra o processo"
                        if p is not None
                        else "o campo não tem um número CNJ de 20 dígitos (numeração antiga "
                        "ou vazio)"
                    ),
                    origem="benner",
                )
            ] += 1
            continue
        proc = dj.get(d)
        if proc is None:
            if datajud_rodou and alias_do_tribunal(d):
                st[
                    "NUMERO_PROCESSO:"
                    + _upsert(
                        db,
                        tenant_id,
                        existentes,
                        vistos=vistos,
                        tipo="NUMERO_PROCESSO",
                        chave=f"NUMERO_PROCESSO|{f.ficha}|nao_encontrado",
                        ficha=f.ficha,
                        cnj=d,
                        campo="Nº processo principal",
                        valor_atual=fmt(d),
                        valor_proposto="conferir o número (o tribunal não o encontra)",
                        confianca="media",
                        evidencia="número válido, mas sem registro no DataJud do tribunal; pode "
                        "ser processo físico, sigiloso, ainda não indexado ou número errado",
                        origem="datajud",
                    )
                ] += 1
            continue
        arq = _ultimo_arquivamento(proc)
        if arq and normalizar(f.situacao) == "em andamento":
            dt, nome = arq
            ult = proc.ultima_movimentacao or dt
            if ult <= dt + timedelta(days=7):  # a baixa é o último movimento: não reativou
                st[
                    "SITUACAO:"
                    + _upsert(
                        db,
                        tenant_id,
                        existentes,
                        vistos=vistos,
                        tipo="SITUACAO",
                        chave=f"SITUACAO|{f.ficha}|encerrado",
                        ficha=f.ficha,
                        cnj=d,
                        campo="Encerramento → Situação",
                        valor_atual=f.situacao,
                        valor_proposto="Encerrado",
                        confianca="alta",
                        evidencia=f"DataJud: '{nome}' em {dt:%d/%m/%Y}, último movimento do "
                        "processo no tribunal",
                        origem="datajud",
                    )
                ] += 1

    # fichas citadas nas prestações que não existem no Benner (só com a carteira importada)
    for a in db.scalars(select(BasaAtoCobrado)) if fichas else []:
        if not a.ficha or a.ficha in por_ficha:
            continue
        if a.cnj in por_cnj:
            continue  # o processo está em outra ficha: o erro é da prestação (FICHA_TROCADA)
        st[
            "FICHA_INEXISTENTE:"
            + _upsert(
                db,
                tenant_id,
                existentes,
                vistos=vistos,
                tipo="FICHA_INEXISTENTE",
                chave=f"FICHA_INEXISTENTE|{a.ficha}|{a.cnj}",
                ficha=a.ficha,
                cnj=a.cnj,
                campo="Ficha",
                valor_atual="(não existe no Benner)",
                valor_proposto="cadastrar a ficha (CCONS) ou corrigir a prestação",
                confianca="media",
                evidencia=f"citada na prestação {a.competencia} ({a.ato_texto[:80]}) e "
                "ausente no export de fichas",
                origem=f"prestacao {a.competencia}",
            )
        ] += 1
    # o que estava pendente e os dados de hoje não confirmam mais (ex.: o processo andou, o
    # tribunal passou a reconhecer o número) sai da fila sozinho
    agora = _agora()
    for c in existentes.values():
        if c.status == "pendente" and c.tipo != "SUBIR_PECA" and c.chave not in vistos:
            c.status = "superado"
            c.historico = [
                *(c.historico or []),
                {"em": agora.isoformat(timespec="seconds"), "por": "sistema", "status": "superado"},
            ]
            st["superados"] += 1
    db.commit()
    return dict(st)


def registrar_pecas(db: Session, tenant_id: uuid.UUID, conferencia: Any) -> dict[str, int]:
    """Do resultado do conferente: cada ato SEM_DOCUMENTO/DOC_DIVERGENTE vira SUBIR_PECA; o que
    agora tem peça e estava pendente/feito vira confirmado."""
    existentes = {c.chave: c for c in db.scalars(select(BennerCorrecao))}
    st: Counter[str] = Counter()
    agora = _agora()
    for c in conferencia.atos:
        ln = c.auditada.linha
        chave = f"SUBIR_PECA|{ln.ficha}|{_dig(ln.cnj)}|{c.auditada.ato_id}|{ln.data}"
        if c.status in ("SEM_DOCUMENTO", "DOC_DIVERGENTE"):
            st[
                _upsert(
                    db,
                    tenant_id,
                    existentes,
                    tipo="SUBIR_PECA",
                    chave=chave,
                    ficha=c.auditada.ficha_sugerida or ln.ficha,
                    cnj=_dig(ln.cnj),
                    campo="Documentos",
                    valor_atual=c.detalhe[:300],
                    valor_proposto=f"{c.auditada.ato_nome or ln.ato_texto} de {ln.data:%d/%m/%Y}"[
                        :300
                    ]
                    if ln.data
                    else (c.auditada.ato_nome or ln.ato_texto)[:300],
                    confianca="alta" if c.status == "SEM_DOCUMENTO" else "media",
                    evidencia=f"prestação {conferencia.competencia}: ato cobrado sem a peça no "
                    "Benner",
                    origem=f"conferencia {conferencia.competencia}",
                )
            ] += 1
        else:
            x = existentes.get(chave[:300])
            if x is not None and x.status in ("pendente", "feito"):
                x.status, x.confirmado_em = "confirmado", agora
                st["confirmados"] += 1
    db.commit()
    return dict(st)


def verificar_com_fichas(db: Session) -> dict[str, int]:
    """Depois de importar um export novo de fichas: confirma o que o Benner já mostra corrigido."""
    fichas = {f.ficha: f for f in db.scalars(select(BasaFicha))}
    agora = _agora()
    st: Counter[str] = Counter()
    for c in db.scalars(
        select(BennerCorrecao).where(BennerCorrecao.status.in_(("pendente", "feito")))
    ):
        f = fichas.get(c.ficha or "")
        ok = False
        if c.tipo == "SITUACAO" and f is not None:
            ok = normalizar(f.situacao) not in ATIVAS or normalizar(f.situacao) == "em encerramento"
        elif c.tipo == "NUMERO_PROCESSO" and f is not None:
            ok = _dig(f.cnj) != _dig(c.cnj) and len(_dig(f.cnj)) == 20
        elif c.tipo == "FICHA_INEXISTENTE":
            ok = f is not None
        if ok:
            c.status, c.confirmado_em = "confirmado", agora
            c.historico = [
                *(c.historico or []),
                {
                    "em": agora.isoformat(timespec="seconds"),
                    "por": "export do Benner",
                    "status": "confirmado",
                },
            ]
            st[c.tipo] += 1
    db.commit()
    return dict(st)


def _item(c: BennerCorrecao) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "tipo": c.tipo,
        "ficha": c.ficha,
        "processo": fmt(c.cnj) if c.cnj else None,
        "campo": c.campo,
        "valor_atual": c.valor_atual,
        "valor_proposto": c.valor_proposto,
        "confianca": c.confianca,
        "evidencia": c.evidencia,
        "origem": c.origem,
        "status": c.status,
        "aplicado_por": c.aplicado_por,
        "aplicado_em": c.aplicado_em.isoformat() if c.aplicado_em else None,
        "confirmado_em": c.confirmado_em.isoformat() if c.confirmado_em else None,
        "observacao": c.observacao,
    }


def listar(
    db: Session, status: str | None = "pendente", tipo: str | None = None, limite: int = 200
) -> dict[str, Any]:
    todos = list(db.scalars(select(BennerCorrecao)))
    resumo: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for c in todos:
        resumo[c.tipo][c.status] += 1
    sel = [c for c in todos if (not status or c.status == status) and (not tipo or c.tipo == tipo)]
    sel.sort(key=lambda c: (TIPOS.index(c.tipo), c.confianca != "alta", c.ficha or ""))
    return {
        "benner_url": BENNER_URL,
        "resumo": {k: dict(v) for k, v in resumo.items()},
        "total": len(sel),
        "itens": [_item(c) for c in sel[:limite]],
    }


def marcar(
    db: Session, cid: uuid.UUID, status: str, por: str, observacao: str | None = None
) -> dict[str, Any]:
    if status not in ("pendente", "feito", "nao_procede"):
        raise ValueError("status inválido")
    if status == "nao_procede" and not (observacao or "").strip():
        raise ValueError("diga o motivo para marcar 'não procede'")
    c = db.get(BennerCorrecao, cid)
    if c is None:
        raise KeyError(cid)
    agora = _agora()
    c.status = status
    if observacao:
        c.observacao = observacao[:2000]
    if status == "feito":
        c.aplicado_por, c.aplicado_em = por[:80], agora
    c.historico = [
        *(c.historico or []),
        {"em": agora.isoformat(timespec="seconds"), "por": por[:80], "status": status},
    ]
    db.commit()
    return _item(c)


def planilha(db: Session, status: str = "pendente") -> bytes:
    """Lote em Excel — para a CCONS aplicar quando o perfil do escritório não puder editar."""
    import io

    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Correções Benner"
    cab = [
        "Tipo",
        "Ficha",
        "Processo",
        "Campo",
        "Valor atual",
        "Corrigir para",
        "Confiança",
        "Evidência",
        "Origem",
        "Status",
    ]
    ws.append(cab)
    for c in ws[1]:
        c.font = Font(bold=True)
    for i in listar(db, status=status, limite=100000)["itens"]:
        ws.append(
            [
                i["tipo"],
                i["ficha"],
                i["processo"],
                i["campo"],
                i["valor_atual"],
                i["valor_proposto"],
                i["confianca"],
                i["evidencia"],
                i["origem"],
                i["status"],
            ]
        )
    for col, w in zip("ABCDEFGHIJ", (18, 18, 26, 24, 30, 34, 10, 70, 18, 12), strict=True):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
