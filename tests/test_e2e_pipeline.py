"""Fluxo M0→M7 pela API com LLM enlatado (sem rede): bootstrap, playbook, intake, autos,
subsídios, antifraude, dossiê, minuta, revisão (423 antes da aprovação) e export DOCX."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.llm import client as llm_client_module
from app.llm.client import LLMClient
from app.modules.m00_playbook.conditions import evaluate_condition, match_thesis
from app.modules.m02_autos.service import DocumentClassification, extract_pages
from app.modules.m05_dossie.service import DossierExtraction, calculated_fields
from app.modules.m06_minuta.service import DraftOutput
from app.modules.m07_revisao.docx_export import CoverInfo, render_docx
from app.modules.m07_revisao.service import review_min_seconds_for

FIXTURES = Path(__file__).parent / "fixtures" / "e2e"
OPS = "ops-key-de-teste-0123456789"


class CannedLLM(LLMClient):
    """Responde com objetos válidos por schema e ainda registra `llm_calls` (modo fake)."""

    def __init__(self) -> None:
        super().__init__(fake=True)

    def structured(self, messages, schema, *, purpose, max_retries=1, **kwargs):  # type: ignore[no-untyped-def,override]
        resp = self.complete(
            messages, purpose=purpose, response_format={"type": "json_object"}, **kwargs
        )
        user = messages[-1]["content"]
        if schema is DocumentClassification:
            nums = [int(n) for n in re.findall(r"### Página (\d+)", user)]
            fname = re.search(r"Arquivo: (\S+)", user).group(1)  # type: ignore[union-attr]
            kind = {
                "contrato.txt": "contrato",
                "comprovante_ted.txt": "comprovante_ted",
                "log_autenticacao.txt": "log_autenticacao",
            }.get(fname, "peticao_inicial")
            pages = []
            for n in nums:
                t = kind
                if kind == "peticao_inicial" and n == 11:
                    t = "procuracao"
                if kind == "peticao_inicial" and n == 12:
                    t = "comprovante_endereco"
                pages.append({"page_number": n, "page_type": t, "confidence": 0.9})
            return DocumentClassification(document_kind=kind, pages=pages), resp
        if schema is DossierExtraction:
            return (
                DossierExtraction(
                    fields={
                        "autor_nega_contratacao": True,
                        "autor_alega_vicio_rmc": False,
                        "autor_pede_gratuidade": True,
                        "renda_declarada_autor": 1518.0,
                        "valor_dano_moral_pedido": 15000.0,
                        "autor_idade": 68,
                        "autor_beneficiario_inss": True,
                        "inicial_atende_requisitos_tema_1198": True,
                        "comprovante_endereco_titular": "autor",
                        "data_procuracao": "2026-09-10",
                    },
                    field_page_refs={"valor_dano_moral_pedido": ["P7"]},
                    facts=[{"text": "A autora nega a contratação.", "page_refs": ["P3"]}],
                    timeline=[{"date": "2024-03-12", "event": "assinatura", "page_refs": ["P13"]}],
                    evidences=[
                        {
                            "description": "TED em conta da autora",
                            "page_refs": ["P15"],
                            "score": 0.9,
                        }
                    ],
                    claims=["inexistência", "repetição em dobro", "dano moral R$ 15.000"],
                    weaknesses=["sem áudio de SAC"],
                    exposure_estimate=29184.0,
                    exposure_basis="dobro + dano moral",
                ),
                resp,
            )
        if schema is DraftOutput:
            return (
                DraftOutput(
                    body_markdown=(
                        "# CONTESTAÇÃO\n\n## Síntese\nA autora nega a contratação [P3].\n\n"
                        "## Do mérito\nO valor foi creditado em conta da autora [P15] e a "
                        "assinatura teve biometria facial [P13]. Ref. inexistente [P99].\n"
                    ),
                    citations=[
                        {"anchor": "nega a contratação", "page_ref": "P3", "evidence_score": 0.8},
                        {"anchor": "creditado em conta", "page_ref": "P15", "evidence_score": 0.95},
                        {"anchor": "inexistente", "page_ref": "P99", "evidence_score": 0.5},
                    ],
                    confidence=0.8,
                    thesis_codes_used=["T06", "T07"],
                    open_questions=["confirmar endereçamento"],
                ),
                resp,
            )
        raise AssertionError(f"schema não previsto: {schema}")


@pytest.fixture
def client(engine, monkeypatch):  # type: ignore[no-untyped-def]
    from app.core import db as core_db
    from app.main import app

    core_db.SessionLocal.configure(bind=engine)
    settings = get_settings()
    monkeypatch.setattr(settings, "ops_key", OPS)
    monkeypatch.setattr(settings, "review_min_seconds_contestacao", 0)
    monkeypatch.setattr(llm_client_module, "_client", CannedLLM())
    from app.workflows import engine as wf

    monkeypatch.setattr(wf, "_engine", None)
    return TestClient(app)


def test_full_pipeline_via_api(client: TestClient) -> None:
    case_fx = json.loads((FIXTURES / "case.json").read_text(encoding="utf-8"))
    password = "senha-de-teste-123456"
    boot = client.post(
        "/ops/bootstrap",
        headers={"X-Ops-Key": OPS},
        json={
            "tenant_name": "FBS Piloto (teste)",
            "tenant_kind": "law_firm",
            "lawyer": {
                "email": "adv@fbs.test",
                "name": "Advogada Teste",
                "oab": "PA 12724",
                "password": password,
            },
            "client": {"name": "Financeira Teste"},
        },
    )
    assert boot.status_code == 200, boot.text
    b = boot.json()
    assert b["tenant_created"] and b["user_created"] and b["client_created"]
    again = client.post(
        "/ops/bootstrap",
        headers={"X-Ops-Key": OPS},
        json={
            "tenant_name": "FBS Piloto (teste)",
            "lawyer": {
                "email": "adv@fbs.test",
                "name": "Advogada Teste",
                "oab": "PA 12724",
                "password": password,
            },
            "client": {"name": "Financeira Teste"},
        },
    ).json()
    assert again["tenant_id"] == b["tenant_id"] and not again["tenant_created"]
    # sem a chave: 404
    assert client.post("/ops/bootstrap", json={}).status_code == 404
    tenant = b["tenant_id"]

    r = client.post(
        "/auth/login", json={"email": "adv@fbs.test", "password": password, "tenant_id": tenant}
    )
    assert r.status_code == 200, r.text
    r = client.post("/auth/mfa", json={"token": r.json()["access_token"], "code": "000000"})
    h = {"X-Tenant-ID": tenant, "Authorization": f"Bearer {r.json()['access_token']}"}
    ops = {**h, "X-Ops-Key": OPS}

    pb = client.post("/ops/playbooks/load?file=consignado-rmc-tjpa", headers=ops)
    assert pb.status_code == 200, pb.text
    assert pb.json()["status"] == "aprovado" and pb.json()["versions_created"] == 14
    pb2 = client.post("/ops/playbooks/load?file=consignado-rmc-tjpa", headers=ops).json()
    assert pb2["versions_created"] == 0 and pb2["versions_reused"] == 14
    theses = client.get("/theses", headers=h).json()
    assert all(t["current_version_id"] for t in theses)

    body = {
        k: v
        for k, v in case_fx.items()
        if not k.startswith("_") and k not in {"subsidies", "fraud_ctx_extra", "expected"}
    }
    body["client_id"] = b["client_id"]
    bad = client.post("/cases", headers=h, json={**body, "cnj_number": "0809999-38.2026.8.14.0301"})
    assert bad.status_code == 422  # dígito verificador errado
    case = client.post("/cases", headers=h, json=body)
    assert case.status_code == 201, case.text
    case_id = case.json()["id"]
    assert case.json()["court"] == "TJPA" and len(case.json()["parties"]) == 3
    assert client.post("/cases", headers=h, json=body).status_code == 409

    pet = (FIXTURES / "peticao_inicial.txt").read_bytes()
    for name, data in [
        ("peticao_inicial.txt", pet),
        ("contrato.txt", (FIXTURES / "contrato.txt").read_bytes()),
        ("comprovante_ted.txt", (FIXTURES / "comprovante_ted.txt").read_bytes()),
        ("log_autenticacao.txt", (FIXTURES / "log_autenticacao.txt").read_bytes()),
    ]:
        up = client.post(
            f"/cases/{case_id}/documents", headers=h, files={"file": (name, data, "text/plain")}
        )
        assert up.status_code == 201, up.text
    docs = client.get(f"/cases/{case_id}/documents", headers=h).json()
    assert len(docs) == 4 and sum(d["page_count"] for d in docs) == 12 + 2 + 1 + 1
    dup = client.post(
        f"/cases/{case_id}/documents",
        headers=h,
        files={"file": ("peticao_inicial.txt", pet, "text/plain")},
    )
    assert (
        dup.status_code == 201
        and len(client.get(f"/cases/{case_id}/documents", headers=h).json()) == 4
    )
    pet_doc = next(d for d in docs if d["filename"] == "peticao_inicial.txt")
    pages = client.get(f"/cases/{case_id}/documents/{pet_doc['id']}/pages", headers=h).json()
    assert [p["page_type"] for p in pages][-2:] == ["procuracao", "comprovante_endereco"]

    r = client.put(f"/cases/{case_id}/subsidies", headers=h, json={"fields": case_fx["subsidies"]})
    assert r.status_code == 200
    ck = client.get(f"/cases/{case_id}/subsidies/checklist", headers=h).json()
    assert ck["blocking_fields_missing"] == [] and "contrato" in ck["present"]

    checks = client.post(
        f"/fraud/cases/{case_id}/run", headers=h, json=case_fx["fraud_ctx_extra"]
    ).json()
    by_code = {c["check_code"]: c for c in checks}
    assert by_code["procuracao_presente"]["result"] == "pass"
    assert by_code["gratuidade_x_renda"]["result"] == "pass"
    assert all(c["human_decision"] is None for c in checks)

    res = client.post(f"/dossiers/cases/{case_id}/build?wait=true", headers=h).json()
    assert res["result"]["status"] == "ready", res
    applicable = res["result"]["applicable_theses"]
    for code in case_fx["expected"]["applicable_theses_min"]:
        assert code in applicable, (code, applicable)
    for code in case_fx["expected"]["not_applicable"]:
        assert code not in applicable
    assert not set(res["result"]["exceptions_triggered"]) & set(
        case_fx["expected"]["exceptions_none_of"]
    )
    dossier = client.get(f"/dossiers/cases/{case_id}", headers=h).json()[0]
    assert dossier["content"]["fields"]["hipotese_afastamento_dano_moral"] == "contratacao_provada"
    assert dossier["content"]["facts"][0]["document_page_ids"]  # P3 resolvido

    res = client.post(
        f"/drafts/cases/{case_id}/generate?wait=true",
        headers=h,
        json={"draft_type": "contestacao"},
    ).json()
    assert "draft_id" in res["result"], res
    assert res["result"]["citations"] == 2 and res["result"]["citations_dropped"] == 1
    assert res["result"]["unresolved_refs"] == ["P99"]
    draft = client.get(f"/drafts/{res['result']['draft_id']}", headers=h).json()
    assert draft["status"] == "generated" and len(draft["citations"]) == 2
    assert "[P15: comprovante_ted.txt, p. 1]" in draft["body_markdown"]
    assert "ALERTAS AO REVISOR" in draft["body_markdown"]
    assert len(draft["thesis_version_ids"]) >= 5

    did = draft["id"]
    assert client.get(f"/reviews/drafts/{did}/export", headers=h).status_code == 423
    review = client.post(f"/reviews/drafts/{did}/open", headers=h).json()
    assert client.get(f"/reviews/drafts/{did}/export", headers=h).status_code == 423
    ap = client.post(f"/reviews/{review['id']}/approve", headers=h)
    assert ap.status_code == 200, ap.text
    assert ap.json()["reviewer_oab"] == "PA 12724"
    docx = client.get(f"/reviews/drafts/{did}/export", headers=h, params={"format": "docx"})
    assert docx.status_code == 200 and docx.content[:2] == b"PK"
    from docx import Document

    text = "\n".join(p.text for p in Document(io.BytesIO(docx.content)).paragraphs)
    assert "MINUTA — revisão obrigatória — gerada em" in text
    assert "playbook consignado-rmc-tjpa v1 aprovado por OAB/PA 12.724" in text
    md = client.get(f"/reviews/drafts/{did}/export", headers=h)
    assert md.status_code == 200 and "aprovado por OAB PA 12724" in md.text

    tr = client.get(f"/ops/cases/{case_id}/trace", headers=ops).json()
    purposes = [c["purpose"] for c in tr["llm_calls"]]
    assert (
        purposes.count("m2.classify_pages") == 4 and "dossier" in purposes and "draft" in purposes
    )
    assert tr["fraud_labels_without_human_decision"] == []
    actions = [a["action"] for a in tr["audit_log"]]
    for must in (
        "case.create",
        "document.upload",
        "fraud_checks.run",
        "dossier.build",
        "draft.generate",
        "review.open",
        "draft.approve",
        "draft.export",
    ):
        assert must in actions
    assert "fraudador" not in draft["body_markdown"].lower()


def test_conditions_evaluator() -> None:
    f: dict[str, Any] = {"a": 10, "s": "rmc", "d": "2024-04-05", "lst": [], "b": False}
    assert evaluate_condition({"campo": "a", "operador": ">", "valor": 5}, f)
    assert not evaluate_condition({"campo": "a", "operador": "<", "valor": 5}, f)
    assert evaluate_condition({"campo": "s", "operador": "in", "valor": ["rmc", "rcc"]}, f)
    assert evaluate_condition({"campo": "d", "operador": ">=", "valor": "2024-01-01"}, f)
    assert evaluate_condition({"campo": "lst", "operador": "nao_existe"}, f)
    assert not evaluate_condition({"campo": "lst", "operador": "existe"}, f)
    assert evaluate_condition({"campo": "b", "operador": "==", "valor": False}, f)
    assert not evaluate_condition({"campo": "zz", "operador": "==", "valor": 1}, f)  # ausente
    m = match_thesis("T01", [{"campo": "a", "operador": ">", "valor": 50}], f)
    assert not m.applicable and m.unmet == ["a > 50"]


def test_calculated_fields_hipoteses() -> None:
    base = {
        "contrato_localizado": True,
        "valor_creditado_conta_autor": True,
        "conta_credito_titularidade": "autor",
        "contrato_assinatura_tipo": "biometria_facial",
        "data_primeiro_desconto": "2024-04-05",
    }
    out = calculated_fields(base)
    assert out["hipotese_afastamento_dano_moral"] == "contratacao_provada"
    assert out["indicio_fraude_contra_autor"] is False
    assert out["data_ciencia_inequivoca"] == "2024-04-05"
    terceiro = calculated_fields({**base, "conta_credito_titularidade": "terceiro"})
    assert terceiro["indicio_fraude_contra_autor"] is True
    assert terceiro["hipotese_afastamento_dano_moral"] == "nenhuma"
    rmc = calculated_fields({**base, "tipo_produto": "rmc", "documento_selfie_coincide": False})
    assert rmc["hipotese_afastamento_dano_moral"] == "rmc_credito_recebido"


def test_extract_pages_text_and_pdf() -> None:
    assert extract_pages(b"a\fb\f\fc", mime_type="text/plain", filename="x.txt") == ["a", "b", "c"]
    assert extract_pages(
        "um\n--- página 2 ---\ndois".encode(), mime_type=None, filename="x.md"
    ) == ["um", "dois"]
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 700, "Pagina um")
    c.showPage()
    c.drawString(50, 700, "Pagina dois")
    c.save()
    pages = extract_pages(buf.getvalue(), mime_type="application/pdf", filename="x.pdf")
    assert len(pages) == 2 and "dois" in pages[1]


def test_review_min_seconds_override_only_in_test_mode(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    settings = get_settings()
    monkeypatch.setattr(settings, "review_min_seconds_contestacao", 900)
    assert review_min_seconds_for("contestacao", None) == 900
    assert review_min_seconds_for("contestacao", {"review_min_seconds": {"contestacao": 30}}) == 900
    assert (
        review_min_seconds_for(
            "contestacao", {"test_mode": True, "review_min_seconds": {"contestacao": 30}}
        )
        == 30
    )
    assert review_min_seconds_for("contestacao", {"test_mode": True, "review_min_seconds": 1}) == 5


def test_docx_cover_block() -> None:
    from datetime import UTC, datetime

    cover = CoverInfo(
        generated_at=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
        playbook_id="consignado-rmc-tjpa",
        playbook_version=1,
        playbook_approved_by_oab="PA 12724",
        reviewer_oab="PA 12724",
        approved_at=datetime(2026, 10, 20, 12, 30, tzinfo=UTC),
        review_seconds=901,
        cnj_number="0809999-39.2026.8.14.0301",
        draft_type="contestacao",
        draft_version=1,
    )
    assert cover.cover_line() == (
        "MINUTA — revisão obrigatória — gerada em 2026-10-20 12:00 UTC — "
        "playbook consignado-rmc-tjpa v1 aprovado por OAB/PA 12.724"
    )
    data = render_docx("# Título\n\n- item **forte** «[REVISOR: data]»\n\nParágrafo.", cover)
    assert data[:2] == b"PK"
