"""N6 — Carteira e investidores: marcação a modelo, concentração, TIR realizada."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PortfolioSnapshot:
    asset_count: int
    invested: float
    mark_to_model: float
    realized: float
    concentration_by_debtor: dict[str, float]

    @property
    def unrealized_gain(self) -> float:
        return self.mark_to_model - self.invested


def concentration(assets: list[tuple[str, float]], top: int = 5) -> dict[str, float]:
    """assets = [(debtor_key, invested)] → share dos `top` maiores devedores."""
    total = sum(v for _, v in assets) or 1.0
    counter: dict[str, float] = {}
    for debtor, invested in assets:
        counter[debtor] = counter.get(debtor, 0.0) + invested
    ranked = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)[:top]
    return {k: v / total for k, v in ranked}
