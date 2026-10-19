"""N5 — Calibração: previsto × realizado por parâmetro.

Brier score para probabilidades; para durações, a próxima iteração usa Kaplan–Meier/Cox
com censura à direita (lifelines). Aqui fica a métrica base e o contrato do job mensal.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


def brier_score(pairs: Iterable[tuple[float, bool]]) -> float:
    """Média de (p − y)². Quanto menor, melhor; 0,25 é o acaso para p = 0,5."""
    pairs = list(pairs)
    if not pairs:
        return float("nan")
    return sum((p - (1.0 if y else 0.0)) ** 2 for p, y in pairs) / len(pairs)


@dataclass
class CalibrationReport:
    parameter: str
    n: int
    brier: float
    mean_predicted: float
    observed_rate: float

    @property
    def bias(self) -> float:
        return self.mean_predicted - self.observed_rate


def calibrate(parameter: str, pairs: list[tuple[float, bool]]) -> CalibrationReport:
    n = len(pairs)
    mean_p = sum(p for p, _ in pairs) / n if n else float("nan")
    obs = sum(1 for _, y in pairs if y) / n if n else float("nan")
    return CalibrationReport(parameter, n, brier_score(pairs), mean_p, obs)
