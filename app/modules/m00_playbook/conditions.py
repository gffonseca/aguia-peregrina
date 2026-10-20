"""Avaliação determinística das condições de aplicação do playbook sobre os campos do dossiê.

As condições são conjunções (AND). Um campo ausente (None / não informado) só satisfaz
`nao_existe`; qualquer outro operador sobre campo ausente resulta em "não aplicável",
nunca em erro — a decisão de usar uma tese sem o campo é do revisor, não da máquina.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

_MISSING: tuple[Any, ...] = (None, "", [], {})


def _present(value: Any) -> bool:
    return not any(value is m or value == m for m in _MISSING)


def _coerce_pair(a: Any, b: Any) -> tuple[Any, Any]:
    """Compara número com número e data com data, tolerando strings ISO vindas do JSON."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a, b
    if isinstance(a, int | float) and isinstance(b, str):
        try:
            return a, float(b)
        except ValueError:
            return a, b
    if isinstance(b, int | float) and isinstance(a, str):
        try:
            return float(a), b
        except ValueError:
            return a, b
    if isinstance(a, str) and isinstance(b, str):
        try:
            return date.fromisoformat(a[:10]), date.fromisoformat(b[:10])
        except ValueError:
            return a, b
    if isinstance(a, datetime | date) and isinstance(b, str):
        try:
            return a, date.fromisoformat(b[:10])
        except ValueError:
            return a, b
    return a, b


def evaluate_condition(cond: Mapping[str, Any], fields: Mapping[str, Any]) -> bool:
    campo = str(cond.get("campo"))
    op = str(cond.get("operador"))
    expected = cond.get("valor")
    value = fields.get(campo)
    if op == "existe":
        return _present(value)
    if op == "nao_existe":
        return not _present(value)
    if not _present(value):
        return False
    if op == "in":
        return value in (expected or [])
    if op == "not_in":
        return value not in (expected or [])
    if op == "contem":
        return expected in value if isinstance(value, list | str) else False
    if op == "nao_contem":
        return expected not in value if isinstance(value, list | str) else False
    a, b = _coerce_pair(value, expected)
    try:
        if op == "==":
            return bool(a == b)
        if op == "!=":
            return bool(a != b)
        if op == ">":
            return bool(a > b)
        if op == ">=":
            return bool(a >= b)
        if op == "<":
            return bool(a < b)
        if op == "<=":
            return bool(a <= b)
    except TypeError:
        return False
    return False


def all_conditions_met(conds: Iterable[Mapping[str, Any]], fields: Mapping[str, Any]) -> bool:
    return all(evaluate_condition(c, fields) for c in conds)


@dataclass(frozen=True)
class ThesisMatch:
    code: str
    applicable: bool
    unmet: list[str]


def match_thesis(code: str, conds: list[dict[str, Any]], fields: Mapping[str, Any]) -> ThesisMatch:
    unmet = [
        f"{c.get('campo')} {c.get('operador')} {c.get('valor', '')}".strip()
        for c in conds
        if not evaluate_condition(c, fields)
    ]
    return ThesisMatch(code=code, applicable=not unmet, unmet=unmet)


__all__ = ["ThesisMatch", "all_conditions_met", "evaluate_condition", "match_thesis"]
