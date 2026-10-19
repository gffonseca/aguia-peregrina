"""Os quatro exemplos da nota técnica (r = 35 % a.a., τ = 34 %), com tolerâncias.

Os alvos vêm de research_notes/.../modelo_de_preco.md §5.3 e do relatório §5.5.
"""

from __future__ import annotations

import pytest

from app.modules.credit.examples import (
    consignado_execucao,
    energia_primeira_instancia,
    trabalhista_ro_pendente,
    voo_pre_ajuizamento,
)
from app.modules.credit.pricing_engine import (
    PricingInputs,
    Scenario,
    ScenarioNode,
    discount_factor,
    minimum_ticket_ok,
    price,
    servicing_pv,
)


def test_discount_factor() -> None:
    assert discount_factor(0.35, 0) == 1.0
    assert discount_factor(0.35, 1) == pytest.approx(1 / 1.35)
    assert discount_factor(0.35, 0.25) == pytest.approx(0.928, abs=0.001)


def test_servicing_pv_is_below_nominal() -> None:
    assert servicing_pv(25, 12, 0.35) < 300
    assert servicing_pv(25, 12, 0.35) > 250


def test_scenario_tree_flattens_and_sums_to_one() -> None:
    tree = ScenarioNode(
        "raiz",
        1.0,
        children=[
            ScenarioNode("a", 0.4, cash_flow=100, t_years=1),
            ScenarioNode(
                "b",
                0.6,
                children=[
                    ScenarioNode("b1", 0.5, cash_flow=50, t_years=2),
                    ScenarioNode("b2", 0.5, cash_flow=0, t_years=2),
                ],
            ),
        ],
    )
    flat = tree.flatten()
    assert len(flat) == 3
    assert sum(s.probability for s in flat) == pytest.approx(1.0)
    assert {s.name for s in flat} == {"raiz/a", "raiz/b/b1", "raiz/b/b2"}


def test_tree_rejects_bad_probabilities() -> None:
    tree = ScenarioNode(
        "raiz",
        1.0,
        children=[
            ScenarioNode("a", 0.5, cash_flow=1, t_years=1),
            ScenarioNode("b", 0.6, cash_flow=1, t_years=1),
        ],
    )
    with pytest.raises(ValueError):
        tree.flatten()


# --------------------------------------------------------------------------- exemplos
def test_i_consignado_execucao() -> None:
    """P_max ≈ R$ 7.250 (72,5 % da face); PV esperado ≈ 9.098; MOIC ≈ 1,49x; ~0,6 ano."""
    r = price(consignado_execucao())
    assert r.pv_expected == pytest.approx(9_098, rel=0.01)
    assert r.pre_tax_price == pytest.approx(8_248, rel=0.01)
    assert r.p_max == pytest.approx(7_250, rel=0.02)
    assert r.price_over_face == pytest.approx(0.725, abs=0.02)
    assert r.expected_moic == pytest.approx(1.49, abs=0.03)
    assert r.expected_duration_years == pytest.approx(0.6, abs=0.1)
    assert 0.80 * 7_250 * 0.95 < r.offer_low < r.offer_high < 0.90 * 7_250 * 1.05
    assert r.viable
    assert minimum_ticket_ok(r)


def test_ii_energia_primeira_instancia_automatizado() -> None:
    """PV esperado ≈ 749; P_max ≈ R$ 480 (≈10 % do pedido, ≈16 % da condenação esperada)."""
    r = price(energia_primeira_instancia(automated=True))
    assert r.pv_expected == pytest.approx(749, rel=0.02)
    assert r.pre_tax_price == pytest.approx(619, rel=0.02)
    assert r.p_max == pytest.approx(480, rel=0.05)
    assert r.price_over_face == pytest.approx(0.10, abs=0.015)
    assert r.price_over_reference == pytest.approx(0.16, abs=0.02)
    assert r.viable


def test_ii_energia_manual_is_not_viable() -> None:
    """Com custos manuais (~830) o preço fica negativo: deal inviável."""
    r = price(energia_primeira_instancia(automated=False))
    assert r.p_max < 0
    assert not r.viable
    assert r.offer_low == 0.0 and r.offer_high == 0.0
    assert not minimum_ticket_ok(r)


def test_iii_trabalhista_ro_pendente() -> None:
    """PV ≈ 14.226; P_max ≈ R$ 9.100 (≈35 % do líquido / ≈23 % da face)."""
    r = price(trabalhista_ro_pendente())
    assert r.pv_expected == pytest.approx(14_226, rel=0.01)
    assert r.pre_tax_price == pytest.approx(12_376, rel=0.01)
    assert r.p_max == pytest.approx(9_100, rel=0.02)
    assert r.price_over_reference == pytest.approx(0.35, abs=0.02)
    assert r.price_over_face == pytest.approx(0.23, abs=0.015)
    assert r.df_bar == pytest.approx(0.5, abs=0.05)


def test_iv_voo_pre_ajuizamento() -> None:
    """PV bruto ≈ 1.525; pré-imposto ≈ 1.005 (20 % do pedido); P_max ≈ R$ 750 (≈15 % do pedido).

    O relatório arredonda P_max para 750; a fórmula exata com DF̄ ≈ 0,74 dá ≈ 650–700.
    Tolerância de 15 % cobre a diferença, e o teste trava o intervalo 'compra só ≤ 15–20 %'.
    """
    r = price(voo_pre_ajuizamento())
    assert r.pv_expected == pytest.approx(1_525, rel=0.01)
    assert r.pre_tax_price == pytest.approx(1_005, rel=0.01)
    assert r.p_max == pytest.approx(750, rel=0.15)
    assert 0.12 <= r.price_over_reference <= 0.20


# --------------------------------------------------------------------------- sensibilidade
def test_sensitivity_lower_irr_raises_price() -> None:
    base = price(consignado_execucao())
    inputs = consignado_execucao()
    inputs.target_irr = 0.25
    assert price(inputs).p_max > base.p_max
    inputs.target_irr = 0.45
    assert price(inputs).p_max < base.p_max


def test_sensitivity_zero_tax_fidc_raises_price_10_to_20_pct() -> None:
    base = price(consignado_execucao())
    inputs = consignado_execucao()
    inputs.tax_rate = 0.0
    up = price(inputs).p_max / base.p_max - 1
    assert 0.10 <= up <= 0.20


def test_sensitivity_doubling_duration_lowers_price() -> None:
    base = price(consignado_execucao())
    doubled = PricingInputs(
        scenarios=[
            Scenario(s.name, s.probability, s.cash_flow, s.t_years * 2) for s in base_inputs()
        ],
        target_irr=0.35,
        tax_rate=0.34,
        c_fix=600,
        c_serv_pv=250,
        face_value=10_000,
    )
    assert price(doubled).p_max < base.p_max * 0.9


def base_inputs() -> list[Scenario]:
    return consignado_execucao().scenarios


def test_params_hash_is_stable_and_sensitive() -> None:
    a = price(consignado_execucao()).params_hash
    b = price(consignado_execucao()).params_hash
    assert a == b
    inputs = consignado_execucao()
    inputs.c_fix += 1
    assert price(inputs).params_hash != a
