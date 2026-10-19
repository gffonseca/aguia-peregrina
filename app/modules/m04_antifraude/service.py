from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.litigation import FraudCheck

OAB_RE = re.compile(r"^[A-Z]{2}\s?\d{1,6}[A-Z]?$")


@dataclass
class CheckOutcome:
    code: str
    result: str  # pass|flag|error
    evidence: dict
    severity: str = "info"


CheckFn = Callable[[dict], CheckOutcome]


def check_oab_format(ctx: dict) -> CheckOutcome:
    oab = (ctx.get("lawyer_oab") or "").replace(".", "").replace("/", " ").strip().upper()
    ok = bool(OAB_RE.match(oab))
    return CheckOutcome("oab_formato", "pass" if ok else "flag", {"oab": oab}, "medium")


def check_power_of_attorney(ctx: dict) -> CheckOutcome:
    present = "procuracao" in set(ctx.get("page_types", []))
    return CheckOutcome("procuracao_presente", "pass" if present else "flag", {}, "high")


def check_address_proof(ctx: dict) -> CheckOutcome:
    present = "comprovante_endereco" in set(ctx.get("page_types", []))
    return CheckOutcome("comprovante_endereco", "pass" if present else "flag", {}, "low")


def check_plaintiff_concentration(ctx: dict) -> CheckOutcome:
    n = int(ctx.get("cases_same_plaintiff_in_portfolio", 0))
    return CheckOutcome("concentracao_autor", "flag" if n >= 3 else "pass", {"cases": n}, "medium")


def check_lawyer_concentration(ctx: dict) -> CheckOutcome:
    n = int(ctx.get("cases_same_lawyer_in_portfolio", 0))
    return CheckOutcome("concentracao_advogado", "flag" if n >= 50 else "pass", {"cases": n}, "low")


def check_lis_pendens(ctx: dict) -> CheckOutcome:
    dup = ctx.get("duplicate_cnj_numbers", [])
    return CheckOutcome("litispendencia", "flag" if dup else "pass", {"cnj": dup}, "high")


def check_gratuity_vs_income(ctx: dict) -> CheckOutcome:
    asks = bool(ctx.get("requests_gratuity"))
    income = ctx.get("declared_income")
    flag = asks and income is not None and income > 5 * 1518.0  # ~5 salários mínimos 2025
    return CheckOutcome(
        "gratuidade_x_renda", "flag" if flag else "pass", {"income": income}, "medium"
    )


DEFAULT_CHECKS: list[CheckFn] = [
    check_oab_format,
    check_power_of_attorney,
    check_address_proof,
    check_plaintiff_concentration,
    check_lawyer_concentration,
    check_lis_pendens,
    check_gratuity_vs_income,
]


def run_checks(
    db: Session, *, tenant_id: uuid.UUID, case_id: uuid.UUID, ctx: dict
) -> list[FraudCheck]:
    rows: list[FraudCheck] = []
    for fn in DEFAULT_CHECKS:
        try:
            out = fn(ctx)
        except Exception as exc:  # noqa: BLE001 - uma checagem não derruba as outras
            out = CheckOutcome(fn.__name__, "error", {"error": str(exc)})
        row = FraudCheck(
            tenant_id=tenant_id,
            case_id=case_id,
            check_code=out.code,
            result=out.result,
            evidence=out.evidence,
            severity=out.severity,
        )
        db.add(row)
        rows.append(row)
    return rows


def human_decide(check: FraudCheck, *, decision: str, oab: str) -> None:
    """Único caminho para confirmar um flag. Sem isto o flag é só 'indício'."""
    if decision not in {"confirmed", "dismissed"}:
        raise ValueError("decisão inválida")
    if not oab:
        raise PermissionError("decisão exige advogado identificado (OAB)")
    check.human_decision = decision
    check.human_decision_by_oab = oab
    check.human_decision_at = datetime.now(UTC)


def has_confirmed_fraud(checks: list[FraudCheck]) -> bool:
    """Só retorna True com aprovação humana. Flags não confirmados nunca viram rótulo."""
    return any(c.result == "flag" and c.human_decision == "confirmed" for c in checks)
