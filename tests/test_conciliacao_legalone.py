"""Conciliação Benner × Legal One: cadastrar, conferir com a CCONS, encerrar no Legal One."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.faturamento import BasaFicha
from app.models.tenant import Tenant
from app.modules.m14_benner.conciliacao import conciliar, ler_legalone

A, B, C, D = (
    "08007677620248140073",
    "00000748420168047801",
    "00000663220154704701",
    "00000793120158044701",
)


def test_conciliacao(db: Session, as_tenant) -> None:  # type: ignore[no-untyped-def]
    t = Tenant(name="FBS conc", kind="law_firm")
    db.add(t)
    db.commit()
    with as_tenant(t.id):
        agora = datetime.now(UTC)
        db.add_all(
            [
                BasaFicha(
                    tenant_id=t.id, ficha="F1", cnj=A, situacao="Em andamento", importado_em=agora
                ),  # só no Benner
                BasaFicha(
                    tenant_id=t.id, ficha="F2", cnj=B, situacao="Encerrado", importado_em=agora
                ),  # L1 ativo
                BasaFicha(
                    tenant_id=t.id, ficha="F3", cnj=D, situacao="Em andamento", importado_em=agora
                ),  # nos dois
            ]
        )
        db.commit()
        txt = (
            f"{B}|false|Proc 1|1\n{C}|false|Proc 2|1\n{D}|false|Proc 3|1\n|false|Proc 4|0\n"
        ).encode()
        l1 = ler_legalone(txt)
        assert len(l1) == 3
        x, r = conciliar(db, l1)
        assert (
            r["cadastrar_no_legalone"] == 1
            and r["conferir_com_ccons"] == 1
            and r["encerrar_no_legalone"] == 1
        )
        assert r["nos_dois"] == 1 and x[:2] == b"PK"
