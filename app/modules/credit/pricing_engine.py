"""N2 — Pricing engine.

Implementa, de forma explícita e testável, a fórmula da nota técnica
(research_notes/.../modelo_de_preco.md §5.1 e relatório §5):

    P_max = [ (1 − τ) · Σ_s π_s · Σ_t CF_{s,t} · DF(t_{s,t}) − C_fix − PV(C_serv) ]
            / (1 − τ · DF̄)

    DF(t) = (1 + r)^(−t)            r = TIR-alvo nominal a.a., t em anos
    DF̄    = Σ_s π_s·CF_s·DF(t_s) / Σ_s π_s·CF_s   (fator médio ponderado pelos recebimentos)
    Oferta = P_max × (1 − margem), margem 10–20 %

A árvore de cenários é parametrizada por tabela (tese × tribunal × réu × fase) e achatada em
cenários terminais; cada terminal tem π_s (produto das condicionais), CF_s e t_s.
Monte Carlo (p10–p90) fica para a próxima iteração; a estrutura já separa "árvore" de "avaliação".
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

METHODOLOGY_VERSION = "2026.10-v1"


# ---------------------------------------------------------------------------
# Estruturas
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Scenario:
    """Cenário terminal: recebe `cash_flow` (líquido ao cessionário) em `t_years`."""

    name: str
    probability: float
    cash_flow: float
    t_years: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(f"probabilidade fora de [0,1] em {self.name}")
        if self.cash_flow < 0 or self.t_years < 0:
            raise ValueError(f"cash_flow/t negativos em {self.name}")


@dataclass
class ScenarioNode:
    """Nó da árvore. Folha quando `cash_flow` é definido; interno quando tem `children`."""

    name: str
    probability: float  # condicional ao pai
    cash_flow: float | None = None
    t_years: float | None = None
    children: list[ScenarioNode] = field(default_factory=list)

    def flatten(self, prefix: str = "", p_acc: float = 1.0) -> list[Scenario]:
        label = f"{prefix}/{self.name}" if prefix else self.name
        p = p_acc * self.probability
        if self.children:
            total = sum(c.probability for c in self.children)
            if abs(total - 1.0) > 1e-6:
                raise ValueError(f"filhos de {label} somam {total:.4f}, não 1")
            out: list[Scenario] = []
            for child in self.children:
                out.extend(child.flatten(label, p))
            return out
        if self.cash_flow is None or self.t_years is None:
            raise ValueError(f"folha {label} sem cash_flow/t_years")
        return [Scenario(label, p, self.cash_flow, self.t_years)]


@dataclass
class PricingInputs:
    scenarios: list[Scenario]
    target_irr: float = 0.35  # r
    tax_rate: float = 0.34  # τ
    c_fix: float = 0.0
    c_serv_pv: float = 0.0  # já em valor presente; ou use `servicing_pv()`
    negotiation_margin: tuple[float, float] = (0.10, 0.20)
    face_value: float | None = None  # base para "% da face"
    reference_value: float | None = None  # base alternativa: líquido esperado, pedido, etc.
    label: str = ""

    def validate(self) -> None:
        total = sum(s.probability for s in self.scenarios)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"cenários somam {total:.4f}, não 1")
        if not 0 <= self.tax_rate < 1:
            raise ValueError("τ deve estar em [0,1)")
        if self.target_irr <= -1:
            raise ValueError("r inválido")


@dataclass
class PricingResult:
    methodology_version: str
    pv_expected: float
    pv_undiscounted: float
    df_bar: float
    costs_total: float
    pre_tax_price: float
    p_max: float
    offer_low: float
    offer_high: float
    expected_moic: float | None
    expected_irr_hint: float
    expected_duration_years: float
    expected_loss_share: float
    p_total_loss: float
    price_over_face: float | None
    price_over_reference: float | None
    viable: bool
    params_hash: str
    scenarios: list[dict]

    def as_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Blocos de cálculo
# ---------------------------------------------------------------------------
def discount_factor(rate: float, t_years: float) -> float:
    """DF(t) = (1 + r)^(−t)."""
    return (1.0 + rate) ** (-t_years)


def servicing_pv(monthly_cost: float, months: int, rate: float) -> float:
    """PV(C_serv) = Σ_{m=1..M} c · DF(m/12)."""
    return sum(monthly_cost * discount_factor(rate, m / 12.0) for m in range(1, months + 1))


def legal_growth_factor(
    t_years: float, ipca_annual: float = 0.0458, legal_rate_annual: float = 0.0877
) -> float:
    """G(t) cível pós-Lei 14.905/2024: IPCA × (1 + Σ TL_m), TL = Selic − IPCA (piso zero).

    Defaults: IPCA 12m 4,58 % (set/2026) e TL ≈ 13,75 % − 4,58 % (juros simples somados).
    """
    months = t_years * 12.0
    monthly_ipca = (1.0 + ipca_annual) ** (1.0 / 12.0) - 1.0
    correction = (1.0 + monthly_ipca) ** months
    simple_interest = 1.0 + (legal_rate_annual / 12.0) * months
    return correction * simple_interest


def net_cash_flow(
    v0: float,
    t_years: float,
    *,
    q: float = 1.0,
    h_contr: float = 0.0,
    d_legais: float = 0.0,
    art523_penalty: bool = False,
    growth_fn=legal_growth_factor,
) -> float:
    """CF_{s,t} = V0 · G(t) · (1 − h_contr) · (1 − d_legais) · q_s [+ multa 10 % art. 523]."""
    base = v0 * growth_fn(t_years) * q
    if art523_penalty:
        base *= 1.10
    return base * (1.0 - h_contr) * (1.0 - d_legais)


def _params_hash(inputs: PricingInputs) -> str:
    payload = {
        "v": METHODOLOGY_VERSION,
        "r": inputs.target_irr,
        "tau": inputs.tax_rate,
        "c_fix": inputs.c_fix,
        "c_serv_pv": inputs.c_serv_pv,
        "scenarios": [asdict(s) for s in inputs.scenarios],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Avaliação
# ---------------------------------------------------------------------------
def price(inputs: PricingInputs) -> PricingResult:
    inputs.validate()
    r, tau = inputs.target_irr, inputs.tax_rate

    pv_expected = 0.0
    pv_undiscounted = 0.0
    duration_num = 0.0
    p_cash = 0.0
    p_total_loss = 0.0
    rows: list[dict] = []
    for s in inputs.scenarios:
        df = discount_factor(r, s.t_years)
        contrib = s.probability * s.cash_flow
        pv_expected += contrib * df
        pv_undiscounted += contrib
        if s.cash_flow > 0:
            p_cash += s.probability
            duration_num += s.probability * s.t_years
        else:
            p_total_loss += s.probability
        rows.append({**asdict(s), "df": df, "pv": contrib * df})

    df_bar = pv_expected / pv_undiscounted if pv_undiscounted > 0 else 1.0
    costs_total = inputs.c_fix + inputs.c_serv_pv
    pre_tax_price = pv_expected - costs_total
    denominator = 1.0 - tau * df_bar
    p_max = ((1.0 - tau) * pv_expected - costs_total) / denominator
    viable = p_max > 0

    lo, hi = inputs.negotiation_margin
    offer_high = p_max * (1.0 - lo) if viable else 0.0
    offer_low = p_max * (1.0 - hi) if viable else 0.0

    expected_moic = (pv_undiscounted / p_max) if viable else None
    expected_duration = duration_num / p_cash if p_cash > 0 else 0.0
    expected_loss_share = (
        1.0 - (pv_undiscounted / _full_value(inputs)) if _full_value(inputs) else 0.0
    )

    face = inputs.face_value
    ref = inputs.reference_value
    return PricingResult(
        methodology_version=METHODOLOGY_VERSION,
        pv_expected=pv_expected,
        pv_undiscounted=pv_undiscounted,
        df_bar=df_bar,
        costs_total=costs_total,
        pre_tax_price=pre_tax_price,
        p_max=p_max,
        offer_low=offer_low,
        offer_high=offer_high,
        expected_moic=expected_moic,
        expected_irr_hint=r,
        expected_duration_years=expected_duration,
        expected_loss_share=max(0.0, expected_loss_share),
        p_total_loss=p_total_loss,
        price_over_face=(p_max / face) if face else None,
        price_over_reference=(p_max / ref) if ref else None,
        viable=viable,
        params_hash=_params_hash(inputs),
        scenarios=rows,
    )


def _full_value(inputs: PricingInputs) -> float:
    """Valor 'cheio' de referência para perda esperada: maior CF entre os cenários."""
    return max((s.cash_flow for s in inputs.scenarios), default=0.0)


def minimum_ticket_ok(result: PricingResult, max_cost_share: float = 0.15) -> bool:
    """Regra de ticket mínimo: C_fix + PV(C_serv) ≤ 10–15 % do PV esperado."""
    if result.pv_expected <= 0:
        return False
    return result.costs_total / result.pv_expected <= max_cost_share
