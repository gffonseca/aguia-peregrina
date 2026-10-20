#!/usr/bin/env python3
"""Ponta a ponta (M0→M7) com um caso SINTÉTICO de consignado não reconhecido, contra a API.

    OPS_KEY_FILE=/caminho/ops_key python scripts/e2e_consignado.py
    AP_BASE_URL=http://localhost:8000 OPS_KEY=... python scripts/e2e_consignado.py --regenerate

Idempotente: tenant/usuário/cliente por nome, playbook por (tipologia, código, versão),
processo por `external_ref`, documentos por sha256, dossiê/minuta reaproveitados quando já
existem (use --regenerate para gerar de novo e gastar LLM). Imprime uma linha do tempo com
duração, tokens e custo por etapa e salva a minuta DOCX/MD em --out.

Variáveis: AP_BASE_URL (default: produção), OPS_KEY ou OPS_KEY_FILE, E2E_PASSWORD (default:
derivada da OPS_KEY, nunca impressa), E2E_TENANT_NAME, E2E_REVIEW_SECONDS (default 30).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "e2e"
DEFAULT_BASE = "https://web-production-c2975.up.railway.app"
PLAYBOOK = "consignado-rmc-tjpa"
LAWYER = {"email": "gustavo.e2e@fbs.adv.br", "name": "Gustavo Fonseca (E2E)", "oab": "PA 12724"}
CLIENT = {"name": "Financeira Teste", "document": "00.000.000/0001-91", "erp_kind": "csv"}


@dataclass
class Step:
    name: str
    seconds: float
    detail: str = ""
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


@dataclass
class Timeline:
    steps: list[Step] = field(default_factory=list)

    def add(self, step: Step) -> None:
        self.steps.append(step)
        print(
            f"  [{step.seconds:6.1f}s] {step.name:<34} {step.detail}"
            + (
                f"  | llm {step.llm_calls} call(s) {step.tokens_in}/{step.tokens_out} tok "
                f"${step.cost_usd:.4f}"
                if step.llm_calls
                else ""
            ),
            flush=True,
        )

    def print_table(self) -> None:
        print("\n== Linha do tempo ==")
        print(
            f"{'etapa':<34}{'dur (s)':>9}{'calls':>7}{'tok in':>9}{'tok out':>9}{'custo US$':>11}"
        )
        for s in self.steps:
            print(
                f"{s.name:<34}{s.seconds:>9.1f}{s.llm_calls:>7}{s.tokens_in:>9}"
                f"{s.tokens_out:>9}{s.cost_usd:>11.4f}"
            )
        print(
            f"{'TOTAL':<34}{sum(s.seconds for s in self.steps):>9.1f}"
            f"{sum(s.llm_calls for s in self.steps):>7}{sum(s.tokens_in for s in self.steps):>9}"
            f"{sum(s.tokens_out for s in self.steps):>9}{sum(s.cost_usd for s in self.steps):>11.4f}"
        )


class Api:
    def __init__(self, base: str, ops_key: str) -> None:
        self.base = base.rstrip("/")
        self.ops_key = ops_key
        self.tenant_id: str | None = None
        self.token: str | None = None
        self.http = httpx.Client(base_url=self.base, timeout=httpx.Timeout(600.0, connect=30.0))

    def headers(self, *, ops: bool = False, auth: bool = True, tenant: bool = True) -> dict:
        h: dict[str, str] = {}
        if tenant and self.tenant_id:
            h["X-Tenant-ID"] = self.tenant_id
        if ops:
            h["X-Ops-Key"] = self.ops_key
        if auth and self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def call(self, method: str, path: str, *, expect: tuple[int, ...] = (200, 201, 202), **kw):
        kw.setdefault("headers", self.headers())
        r = self.http.request(method, path, **kw)
        if r.status_code not in expect:
            raise SystemExit(f"{method} {path} → {r.status_code}: {r.text[:800]}")
        return r


def load_ops_key() -> str:
    if os.environ.get("OPS_KEY"):
        return os.environ["OPS_KEY"].strip()
    path = os.environ.get("OPS_KEY_FILE")
    if path and Path(path).exists():
        return Path(path).read_text(encoding="utf-8").strip()
    raise SystemExit("defina OPS_KEY ou OPS_KEY_FILE")


def petition_pdf(text_pages: list[str]) -> bytes | None:
    """Gera um PDF simples (reportlab) para exercitar a extração por pypdf; None se indisponível."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import simpleSplit
        from reportlab.pdfgen import canvas
    except ImportError:
        return None
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, invariant=1)  # sem timestamp: bytes estáveis → sha estável
    width, height = A4
    for page in text_pages:
        y = height - 60
        c.setFont("Helvetica", 10)
        for para in page.split("\n"):
            lines = simpleSplit(para, "Helvetica", 10, width - 120) or [""]
            for line in lines:
                if y < 50:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = height - 60
                c.drawString(60, y, line)
                y -= 13
            y -= 4
        c.showPage()
    c.save()
    return buf.getvalue()


def wait_job(api: Api, res: dict, *, timeout: float = 900.0) -> dict:
    """Dossiê/minuta rodam em background (proxy do Railway corta HTTP em ~5 min): faz polling."""
    if not res.get("async"):
        return res.get("result") or {}
    ref = res["job"]
    started = time.perf_counter()
    while True:
        st = api.call("GET", f"/jobs/{ref}").json()
        if st["status"] == "done":
            return st.get("result") or {}
        if st["status"] == "failed":
            raise SystemExit(f"job {ref} falhou: {st.get('error')}")
        if time.perf_counter() - started > timeout:
            raise SystemExit(f"job {ref} não terminou em {timeout:.0f}s")
        time.sleep(5)


def trace_totals(trace: dict, since_ids: set[str]) -> tuple[int, int, int, float, set[str]]:
    calls = [c for c in trace["llm_calls"] if c["id"] not in since_ids]
    ids = {c["id"] for c in trace["llm_calls"]}
    return (
        len(calls),
        sum(c["input_tokens"] or 0 for c in calls),
        sum(c["output_tokens"] or 0 for c in calls),
        sum(c["cost_usd"] or 0.0 for c in calls),
        ids,
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--base-url", default=os.environ.get("AP_BASE_URL", DEFAULT_BASE))
    ap.add_argument("--out", default=os.environ.get("E2E_OUT", str(ROOT / "out" / "e2e")))
    ap.add_argument("--regenerate", action="store_true", help="refaz dossiê e minuta (gasta LLM)")
    ap.add_argument(
        "--review-seconds", type=int, default=int(os.environ.get("E2E_REVIEW_SECONDS", "30"))
    )
    ap.add_argument(
        "--tenant-name", default=os.environ.get("E2E_TENANT_NAME", "FBS Piloto (E2E sintético)")
    )
    ap.add_argument(
        "--no-pdf", action="store_true", help="envia a inicial como texto em vez de PDF"
    )
    args = ap.parse_args()

    ops_key = load_ops_key()
    password = (
        os.environ.get("E2E_PASSWORD")
        or hashlib.sha256((ops_key + ":e2e-consignado").encode()).hexdigest()[:24]
    )
    api = Api(args.base_url, ops_key)
    tl = Timeline()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    case_fx = json.loads((FIXTURES / "case.json").read_text(encoding="utf-8"))
    print(f"== Águia Peregrina E2E · {api.base} · caso sintético {case_fx['cnj_number']} ==")

    # ---------------------------------------------------------------- 0. health
    t0 = time.perf_counter()
    h = api.call("GET", "/health", headers={}).json()
    llm = api.call("GET", "/health/llm", headers={}).json()
    tl.add(Step("health", time.perf_counter() - t0, f"env={h['env']} llm={llm['effective']}"))
    if llm["effective"] != "live":
        print("AVISO: LLM em modo fake; dossiê/minuta sairão vazios")

    # ---------------------------------------------------------------- 1. bootstrap
    t0 = time.perf_counter()
    boot = api.call(
        "POST",
        "/ops/bootstrap",
        headers=api.headers(ops=True, auth=False, tenant=False),
        json={
            "tenant_name": args.tenant_name,
            "tenant_kind": "law_firm",
            "tenant_settings": {
                "test_mode": True,
                "review_min_seconds": {
                    "contestacao": args.review_seconds,
                    "default": args.review_seconds,
                },
                "note": "tenant sintético do E2E; test_mode reduz o tempo mínimo de revisão",
            },
            "lawyer": {**LAWYER, "role": "partner", "password": password},
            "client": CLIENT,
        },
    ).json()
    api.tenant_id = boot["tenant_id"]
    tl.add(
        Step(
            "M0 bootstrap tenant/advogado/cliente",
            time.perf_counter() - t0,
            f"tenant={boot['tenant_id'][:8]}… created={boot['tenant_created']} "
            f"user_created={boot['user_created']} client={str(boot['client_id'])[:8]}…",
        )
    )

    # ---------------------------------------------------------------- 1b. login + MFA
    t0 = time.perf_counter()
    r = api.call(
        "POST",
        "/auth/login",
        headers={},
        json={"email": LAWYER["email"], "password": password, "tenant_id": api.tenant_id},
    ).json()
    r = api.call(
        "POST",
        "/auth/mfa",
        headers={},
        json={"token": r["access_token"], "code": boot["mfa_dev_code"]},
    ).json()
    api.token = r["access_token"]
    tl.add(Step("auth login + MFA (placeholder)", time.perf_counter() - t0, f"OAB {LAWYER['oab']}"))

    # ---------------------------------------------------------------- 1c. playbook
    t0 = time.perf_counter()
    pb = api.call(
        "POST", f"/ops/playbooks/load?file={PLAYBOOK}", headers=api.headers(ops=True)
    ).json()
    tl.add(
        Step(
            "M0 playbook → theses (aprovado)",
            time.perf_counter() - t0,
            f"{pb['playbook_id']} v{pb['versao']} {pb['status']} teses={pb['theses']} "
            f"novas={pb['versions_created']} reuso={pb['versions_reused']} OAB={pb['approved_by_oab']}",
        )
    )

    # ---------------------------------------------------------------- 2. M1 intake
    t0 = time.perf_counter()
    existing = api.call("GET", "/cases", params={"external_ref": case_fx["external_ref"]}).json()
    if existing:
        case = existing[0]
        how = "reuso"
    else:
        body = {
            k: v
            for k, v in case_fx.items()
            if not k.startswith("_") and k not in {"subsidies", "fraud_ctx_extra", "expected"}
        }
        body["client_id"] = boot["client_id"]
        case = api.call("POST", "/cases", json=body).json()
        how = "criado"
    case_id = case["id"]
    tl.add(
        Step(
            "M1 intake (caso + partes)",
            time.perf_counter() - t0,
            f"{how} {case['cnj_number']} {case['court']} id={case_id[:8]}…",
        )
    )

    seen_ids: set[str] = {
        c["id"]
        for c in api.call(
            "GET", f"/ops/cases/{case_id}/trace", headers=api.headers(ops=True)
        ).json()["llm_calls"]
    }

    # ---------------------------------------------------------------- 3. M2 documentos
    t0 = time.perf_counter()
    pet_pages = (FIXTURES / "peticao_inicial.txt").read_text(encoding="utf-8").split("\f")
    uploads: list[tuple[str, bytes, str]] = []
    pdf = None if args.no_pdf else petition_pdf(pet_pages)
    if pdf:
        uploads.append(("peticao_inicial.pdf", pdf, "application/pdf"))
    else:
        uploads.append(("peticao_inicial.txt", "\f".join(pet_pages).encode(), "text/plain"))
    for name in ("contrato.txt", "comprovante_ted.txt", "log_autenticacao.txt"):
        uploads.append((name, (FIXTURES / name).read_bytes(), "text/plain"))
    docs = []
    for name, data, mime in uploads:
        d = api.call(
            "POST", f"/cases/{case_id}/documents", files={"file": (name, data, mime)}
        ).json()
        docs.append(d)
    pages_total = sum(d.get("page_count") or 0 for d in docs)
    tr = api.call("GET", f"/ops/cases/{case_id}/trace", headers=api.headers(ops=True)).json()
    n, ti, to, cost, seen_ids = trace_totals(tr, seen_ids)
    tl.add(
        Step(
            "M2 upload + extração + classificação",
            time.perf_counter() - t0,
            f"{len(docs)} docs, {pages_total} páginas; kinds="
            + ",".join(str(d.get("kind")) for d in docs),
            n,
            ti,
            to,
            cost,
        )
    )

    # ---------------------------------------------------------------- 4. M3 subsídios
    t0 = time.perf_counter()
    api.call(
        "PUT",
        f"/cases/{case_id}/subsidies",
        json={"fields": case_fx["subsidies"], "source_ref": "ERP-TESTE/CCB-TESTE-2024-000123"},
    )
    ck = api.call("GET", f"/cases/{case_id}/subsidies/checklist").json()
    tl.add(
        Step(
            "M3 subsídios + checklist",
            time.perf_counter() - t0,
            f"faltam={ck['missing'] or '—'} campos_subsidio_faltando={len(ck['subsidy_fields_missing'])} "
            f"bloqueantes={ck['blocking_fields_missing'] or '—'}",
        )
    )

    # ---------------------------------------------------------------- 5. M4 antifraude
    t0 = time.perf_counter()
    checks = api.call(
        "POST", f"/fraud/cases/{case_id}/run", json=case_fx.get("fraud_ctx_extra", {})
    ).json()
    flags = [c["check_code"] for c in checks if c["result"] == "flag"]
    assert all(c["human_decision"] is None for c in checks), "antifraude não pode decidir sozinho"
    tl.add(
        Step(
            "M4 antifraude (determinístico)",
            time.perf_counter() - t0,
            f"{len(checks)} checagens; flags={flags or '—'}; rótulos humanos=0",
        )
    )

    # ---------------------------------------------------------------- 6. M5 dossiê
    t0 = time.perf_counter()
    dossiers = [
        d for d in api.call("GET", f"/dossiers/cases/{case_id}").json() if d["status"] == "ready"
    ]
    if dossiers and not args.regenerate:
        dossier = sorted(dossiers, key=lambda d: d["version"])[-1]
        how = "reuso"
    else:
        res = api.call("POST", f"/dossiers/cases/{case_id}/build", json={}).json()
        result = wait_job(api, res)
        if result.get("error"):
            raise SystemExit(f"dossiê falhou: {result}")
        dossier = next(
            d
            for d in api.call("GET", f"/dossiers/cases/{case_id}").json()
            if d["id"] == result["dossier_id"]
        )
        how = "gerado"
    content = dossier["content"]
    applicable = [t["code"] for t in content.get("applicable_theses", [])]
    exceptions = [x["id"] for x in content.get("exceptions_triggered", [])]
    tr = api.call("GET", f"/ops/cases/{case_id}/trace", headers=api.headers(ops=True)).json()
    n, ti, to, cost, seen_ids = trace_totals(tr, seen_ids)
    tl.add(
        Step(
            "M5 dossiê (LLM estruturado)",
            time.perf_counter() - t0,
            f"{how} v{dossier['version']} fatos={len(content.get('facts', []))} provas={len(content.get('evidences', []))} "
            f"teses={applicable} exceções={exceptions or '—'} exposição={dossier.get('exposure_estimate')}",
            n,
            ti,
            to,
            cost,
        )
    )
    (out_dir / "dossier.json").write_text(
        json.dumps(dossier, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    exp = case_fx.get("expected", {})
    missing_expected = [t for t in exp.get("applicable_theses_min", []) if t not in applicable]
    wrong = [t for t in exp.get("not_applicable", []) if t in applicable]
    bad_x = [x for x in exp.get("exceptions_none_of", []) if x in exceptions]
    if missing_expected or wrong or bad_x:
        print(
            f"  AVISO playbook: esperadas ausentes={missing_expected} indevidas={wrong} exceções indevidas={bad_x}"
        )

    # ---------------------------------------------------------------- 7. M6 minuta
    t0 = time.perf_counter()
    drafts = api.call("GET", f"/drafts/cases/{case_id}").json()
    reusable = [
        d
        for d in drafts
        if d["status"] in {"generated", "in_review", "approved"}
        and d["dossier_id"] == dossier["id"]
    ]
    if reusable and not args.regenerate:
        draft = sorted(reusable, key=lambda d: d["version"])[-1]
        how = "reuso"
    else:
        res = api.call(
            "POST",
            f"/drafts/cases/{case_id}/generate",
            json={"draft_type": "contestacao", "dossier_id": dossier["id"]},
        ).json()
        result = wait_job(api, res)
        if result.get("error"):
            raise SystemExit(f"minuta falhou: {result}")
        draft = api.call("GET", f"/drafts/{result['draft_id']}").json()
        how = "gerada"
    body = draft["body_markdown"]
    # a peça em si (sem o bloco de alertas ao revisor) não pode rotular o autor
    piece = "\n".join(line for line in body.splitlines() if not line.startswith(">"))
    for forbidden in ("fraudador", "fraudadora", "litigante de má-fé", "estelionat"):
        assert forbidden not in piece.lower(), f"minuta rotula o autor: {forbidden!r}"
    tr = api.call("GET", f"/ops/cases/{case_id}/trace", headers=api.headers(ops=True)).json()
    n, ti, to, cost, seen_ids = trace_totals(tr, seen_ids)
    tl.add(
        Step(
            "M6 minuta (teses + citações)",
            time.perf_counter() - t0,
            f"{how} v{draft['version']} status={draft['status']} teses={len(draft['thesis_version_ids'])} "
            f"citações={len(draft['citations'])} confiança={draft['confidence']} chars={len(body)}",
            n,
            ti,
            to,
            cost,
        )
    )
    (out_dir / "minuta.md").write_text(body, encoding="utf-8")

    # ---------------------------------------------------------------- 8. M7 revisão
    t0 = time.perf_counter()
    draft_id = draft["id"]
    if draft["status"] not in {"approved", "exported"}:
        blocked = api.http.get(f"/reviews/drafts/{draft_id}/export", headers=api.headers())
        assert blocked.status_code == 423, (
            f"export sem revisão deveria ser 423, veio {blocked.status_code}"
        )
        review = api.call("POST", f"/reviews/drafts/{draft_id}/open").json()
        blocked = api.http.get(f"/reviews/drafts/{draft_id}/export", headers=api.headers())
        assert blocked.status_code == 423, (
            "export com revisão aberta (sem aprovação) deveria ser 423"
        )
        early = api.http.post(f"/reviews/{review['id']}/approve", headers=api.headers())
        early_note = f"aprovação imediata → {early.status_code}"
        waited = 0.0
        while True:
            r = api.http.post(f"/reviews/{review['id']}/approve", headers=api.headers())
            if r.status_code == 200:
                review = r.json()
                break
            if r.status_code != 409:
                raise SystemExit(f"approve → {r.status_code}: {r.text}")
            time.sleep(5)
            waited += 5
            if waited > args.review_seconds + 120:
                raise SystemExit("tempo mínimo de revisão não liberou")
        note = f"{early_note}; aprovada por OAB {review['reviewer_oab']} após {review['review_seconds']}s"
    else:
        review = api.call("GET", f"/reviews/drafts/{draft_id}").json()[-1]
        note = f"já aprovada por OAB {review['reviewer_oab']}"
    docx = api.call("GET", f"/reviews/drafts/{draft_id}/export", params={"format": "docx"})
    docx_path = out_dir / f"minuta-{case['cnj_number']}-contestacao-v{draft['version']}.docx"
    docx_path.write_bytes(docx.content)
    md = api.call("GET", f"/reviews/drafts/{draft_id}/export", params={"format": "md"})
    (out_dir / "minuta-exportada.md").write_text(md.text, encoding="utf-8")
    tl.add(
        Step(
            "M7 revisão (423 → aprovação) + DOCX",
            time.perf_counter() - t0,
            f"{note}; docx={len(docx.content)} bytes",
        )
    )

    # ---------------------------------------------------------------- 9. verificação
    t0 = time.perf_counter()
    tr = api.call("GET", f"/ops/cases/{case_id}/trace", headers=api.headers(ops=True)).json()
    (out_dir / "trace.json").write_text(
        json.dumps(tr, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    assert not tr["fraud_labels_without_human_decision"], tr["fraud_labels_without_human_decision"]
    assert all(c["human_decision"] is None for c in tr["fraud_checks"]), (
        "nenhuma decisão humana deveria existir"
    )
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
        assert must in actions, f"audit_log sem {must}: {actions}"
    bad = [c for c in tr["llm_calls"] if c["status"] != "ok"]
    tl.add(
        Step(
            "verificação (llm_calls, audit, fraude)",
            time.perf_counter() - t0,
            f"llm_calls={tr['llm_totals']['calls']} (erros={len(bad)}) custo_total=${tr['llm_totals']['cost_usd']:.4f} "
            f"audit={len(actions)} eventos; flags={len([c for c in tr['fraud_checks'] if c['result'] == 'flag'])} sem rótulo humano",
        )
    )

    tl.print_table()
    print("\n== llm_calls do caso ==")
    for c in tr["llm_calls"]:
        print(
            f"  {c['purpose']:<18}{c['model']:<14}{str(c['provider_model']):<30}{c['input_tokens'] or 0:>7}/{c['output_tokens'] or 0:<6}{(c['latency_ms'] or 0) / 1000:>7.1f}s  ${c['cost_usd'] or 0:.4f}  {c['status']}"
        )
    print(
        f"\nDOCX: {docx_path}\nMD:   {out_dir / 'minuta-exportada.md'}\nDossiê: {out_dir / 'dossier.json'}\nTrace: {out_dir / 'trace.json'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
