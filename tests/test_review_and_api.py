"""Princípios OAB no código: export bloqueado sem aprovação; recusa com motivo; fraude só humana."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import Principal, issue_token
from app.models.litigation import Case, Draft, FraudCheck
from app.modules.m04_antifraude.service import has_confirmed_fraud, human_decide
from app.modules.m07_revisao.service import (
    ReviewError,
    approve,
    assert_exportable,
    open_review,
    reject,
)


def test_export_blocked_until_approved(db, two_tenants, as_tenant) -> None:  # type: ignore[no-untyped-def]
    a, _ = two_tenants
    with as_tenant(a):
        case = Case(cnj_number="0000006-66.2026.8.14.0301")
        db.add(case)
        db.flush()
        draft = Draft(case_id=case.id, draft_type="contestacao", body_markdown="# minuta")
        db.add(draft)
        db.flush()
        with pytest.raises(ReviewError):
            assert_exportable(draft, None)
        review = open_review(
            db, tenant_id=a, draft=draft, reviewer_user_id=uuid.uuid4(), reviewer_oab="PA 12724"
        )
        with pytest.raises(ReviewError):
            assert_exportable(draft, review)
        approve(review, draft)
        assert_exportable(draft, review)
        assert draft.status == "approved"


def test_minimum_review_time_enforced(db, two_tenants, as_tenant, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    a, _ = two_tenants
    settings = get_settings()
    monkeypatch.setattr(settings, "review_min_seconds_contestacao", 900)
    with as_tenant(a):
        case = Case(cnj_number="0000007-77.2026.8.14.0301")
        db.add(case)
        db.flush()
        draft = Draft(case_id=case.id, draft_type="contestacao", body_markdown="x")
        db.add(draft)
        db.flush()
        review = open_review(
            db, tenant_id=a, draft=draft, reviewer_user_id=uuid.uuid4(), reviewer_oab="PA 1"
        )
        with pytest.raises(ReviewError):
            approve(review, draft, now=review.opened_at + timedelta(seconds=60))
        approve(review, draft, now=review.opened_at + timedelta(seconds=901))
        assert review.review_seconds == 901


def test_reject_requires_reason(db, two_tenants, as_tenant) -> None:  # type: ignore[no-untyped-def]
    a, _ = two_tenants
    with as_tenant(a):
        case = Case(cnj_number="0000008-88.2026.8.14.0301")
        db.add(case)
        db.flush()
        draft = Draft(case_id=case.id, draft_type="contestacao", body_markdown="x")
        db.add(draft)
        db.flush()
        review = open_review(
            db, tenant_id=a, draft=draft, reviewer_user_id=uuid.uuid4(), reviewer_oab="PA 1"
        )
        with pytest.raises(ReviewError):
            reject(review, draft, reason="não")
        reject(review, draft, reason="tese inaplicável ao caso concreto")
        assert draft.status == "rejected"


def test_fraud_label_requires_human_decision() -> None:
    flag = FraudCheck(check_code="litispendencia", result="flag", evidence={}, severity="high")
    assert not has_confirmed_fraud([flag])
    with pytest.raises(PermissionError):
        human_decide(flag, decision="confirmed", oab="")
    human_decide(flag, decision="confirmed", oab="PA 12724")
    assert has_confirmed_fraud([flag])
    assert flag.human_decision_at is not None and flag.human_decision_at.tzinfo is UTC


def test_health_and_tenant_header() -> None:
    from app.main import app

    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/cases").status_code == 400  # sem X-Tenant-ID


def test_pricing_endpoint_runs_example(db, two_tenants) -> None:  # type: ignore[no-untyped-def]
    from app.main import app

    a, _ = two_tenants
    settings = get_settings()
    principal = Principal(uuid.uuid4(), a, "lawyer", "PA 1", mfa_verified=True)
    token = issue_token(principal, settings)
    client = TestClient(app)
    headers = {"X-Tenant-ID": str(a), "Authorization": f"Bearer {token}"}
    r = client.get("/pricing/examples/consignado_execucao", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["p_max"] == pytest.approx(7250, rel=0.02)
    # token de outro tenant é recusado
    other = {"X-Tenant-ID": str(uuid.uuid4()), "Authorization": f"Bearer {token}"}
    assert client.get("/pricing/examples/consignado_execucao", headers=other).status_code == 403
    assert datetime.now(UTC).year >= 2026
