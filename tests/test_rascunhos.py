"""IA redige: fontes reais (ficha, DataJud, intimação do DJEN) no prompt, aviso e .docx."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.faturamento import BasaFicha, DataJudProcesso, MotorExecucao, MotorOportunidade
from app.models.tenant import Tenant
from app.models.triagem import TriagemEmail
from app.modules.m12_faturamento import rascunhos

CNJ = "08007677620248140073"


class FakeLLM:
    def __init__(self) -> None:
        self.msgs: list[dict[str, Any]] = []

    def complete(self, messages: list[dict[str, Any]], **_: Any) -> Any:
        self.msgs = messages

        class R:
            content = "```markdown\n# EXCELENTÍSSIMO\n\n**Apelação** — razões\n\n- pedido 1\n```"
            provider_model = "fake/claude"

        return R()


def test_rascunho_com_intimacao(db: Session, as_tenant) -> None:  # type: ignore[no-untyped-def]
    t = Tenant(name="FBS rascunho IA", kind="law_firm")
    db.add(t)
    db.commit()
    with as_tenant(t.id):
        db.add(
            BasaFicha(
                tenant_id=t.id,
                ficha="CIVE.1/2024",
                cnj=CNJ,
                situacao="Em andamento",
                adverso="Fulano de Tal",
                importado_em=datetime.now(UTC),
            )
        )
        db.add(
            DataJudProcesso(
                tenant_id=t.id,
                cnj=CNJ,
                tribunal="TJPA",
                classe="Execução de Título Extrajudicial",
                graus={"g": {"movimentos": [[220, "Improcedência", "2026-09-01", []]]}},
                buscado_em=datetime.now(UTC),
            )
        )
        db.add(
            TriagemEmail(
                tenant_id=t.id,
                mensagem_id="djen:1",
                caixa="djen",
                recebido_em=datetime(2026, 9, 2, tzinfo=UTC),
                remetente="djen@x",
                assunto="DJEN — Intimação",
                categoria="INTIMACAO",
                urgencia="alta",
                papeis=["prazos_pa"],
                cnjs=[CNJ],
                fichas=[],
                texto_integral="SENTENÇA. Julgo improcedentes os embargos do Banco.",
            )
        )
        ex = MotorExecucao(
            tenant_id=t.id, iniciado_em=datetime.now(UTC), referencia=date(2026, 10, 1), status="ok"
        )
        db.add(ex)
        db.commit()
        db.add(
            MotorOportunidade(
                tenant_id=t.id,
                execucao_id=ex.id,
                cnj=CNJ,
                evento="sentenca_desfavoravel",
                data_evento=date(2026, 9, 1),
                ato_id="apelacao",
                valor=250,
                papel="redige",
                confianca="alta",
                status="ABERTA",
                movimento="220 Improcedência",
            )
        )
        db.commit()
        llm = FakeLLM()
        r = rascunhos.gerar(
            db, t.id, CNJ, "sentenca_desfavoravel", date(2026, 9, 1), "ana@fbs", llm=llm
        )
        prompt = llm.msgs[1]["content"]
        assert (
            "Julgo improcedentes" in prompt
            and "Fulano de Tal" in prompt
            and "Improcedência" in prompt
        )
        assert "não cite súmula" in llm.msgs[0]["content"]
        assert r.conteudo.startswith("> **RASCUNHO GERADO POR IA")
        assert "```" not in r.conteudo and r.fontes["intimacao_djen"] is True
        assert rascunhos.docx(r)[:2] == b"PK"
        try:
            rascunhos.gerar(db, t.id, CNJ, "outro", date(2026, 9, 1), "x", llm=llm)
            raise AssertionError
        except KeyError:
            pass
