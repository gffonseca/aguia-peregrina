"""Os quatro exemplos trabalhados da nota técnica (r = 35 % a.a., τ = 34 %).

Usados como fixtures de teste e como documentação executável do pricing engine.
Cash flows e prazos são os do relatório (já líquidos ao cessionário).
"""

from __future__ import annotations

from app.modules.credit.pricing_engine import PricingInputs, Scenario, ScenarioNode

R = 0.35
TAU = 0.34


def consignado_execucao() -> PricingInputs:
    """(i) Consignado não reconhecido — R$ 10.000 em cumprimento de sentença (TJPA), réu banco."""
    scenarios = [
        Scenario("deposito_voluntario_3m", 0.45, 10_330.0, 3 / 12),
        Scenario("sisbajud_alvara_9m_multa523", 0.45, 12_115.0, 9 / 12),
        Scenario("impugnacao_parcial_-30pct_18m", 0.08, 8_491.0, 18 / 12),
        Scenario("perda", 0.02, 0.0, 18 / 12),
    ]
    return PricingInputs(
        scenarios=scenarios,
        target_irr=R,
        tax_rate=TAU,
        c_fix=600.0,
        c_serv_pv=250.0,
        face_value=10_000.0,
        reference_value=10_000.0,
        label="(i) consignado — cumprimento de sentença",
    )


def energia_primeira_instancia(automated: bool = True) -> PricingInputs:
    """(ii) Falha de energia — pedido R$ 5.000, JEC 1ª instância, réu concessionária."""
    tree = ScenarioNode(
        "raiz",
        1.0,
        children=[
            ScenarioNode("acordo_audiencia", 0.25, cash_flow=1_260.0, t_years=4 / 12),
            # O relatório grafa 43,75 %, mas 0,75 × (1 − p_proc 0,55) = 33,75 %; como o CF é
            # zero o PV não muda (285 + 236 + 228 = 749). Corrigido para fechar a árvore em 1.
            ScenarioNode("extincao_ou_improcedencia", 0.3375, cash_flow=0.0, t_years=1.0),
            ScenarioNode(
                "procedencia_3000",
                0.4125,
                children=[
                    ScenarioNode("sem_recurso", 0.40, cash_flow=2_240.0, t_years=1.5),
                    ScenarioNode("recurso_mantido", 0.45, cash_flow=2_450.0, t_years=2.3),
                    ScenarioNode("reformado", 0.15, cash_flow=0.0, t_years=2.3),
                ],
            ),
        ],
    )
    costs_fix, costs_serv = (50.0, 80.0) if automated else (450.0, 380.0)
    return PricingInputs(
        scenarios=tree.flatten(),
        target_irr=R,
        tax_rate=TAU,
        c_fix=costs_fix,
        c_serv_pv=costs_serv,
        face_value=5_000.0,
        reference_value=3_000.0,  # condenação esperada
        label=f"(ii) energia — 1ª instância ({'automatizado' if automated else 'manual'})",
    )


def trabalhista_ro_pendente() -> PricingInputs:
    """(iii) Reclamação trabalhista — R$ 40.000 brutos, RO do réu pendente no TRT-8."""
    liquido = 40_000.0 * (1 - 0.30) * (1 - 0.08)  # ≈ 25.760 (relatório arredonda para 26.000)
    tree = ScenarioNode(
        "raiz",
        1.0,
        children=[
            ScenarioNode("acordo_trt", 0.15, cash_flow=19_500.0, t_years=0.8),
            ScenarioNode(
                "trt_mantem",
                0.595,
                children=[
                    ScenarioNode("sem_rr", 0.65, cash_flow=33_200.0, t_years=2.0),
                    ScenarioNode("rr_mantido", 0.315, cash_flow=40_900.0, t_years=3.7),
                    ScenarioNode("rr_provido", 0.035, cash_flow=0.0, t_years=3.7),
                ],
            ),
            ScenarioNode("trt_reduz_20pct", 0.17, cash_flow=27_600.0, t_years=2.3),
            ScenarioNode("reforma_total", 0.085, cash_flow=0.0, t_years=1.0),
        ],
    )
    return PricingInputs(
        scenarios=tree.flatten(),
        target_irr=R,
        tax_rate=TAU,
        c_fix=1_300.0,
        c_serv_pv=550.0,
        face_value=40_000.0,
        reference_value=liquido,
        label="(iii) trabalhista — RO pendente",
    )


def voo_pre_ajuizamento() -> PricingInputs:
    """(iv) Pré-ajuizamento — cancelamento de voo, pedido R$ 5.000 (pipeline próprio, h=0)."""
    tree = ScenarioNode(
        "raiz",
        1.0,
        children=[
            ScenarioNode("acordo_extrajudicial", 0.20, cash_flow=1_200.0, t_years=1 / 12),
            ScenarioNode(
                "ajuizamento",
                0.80,
                children=[
                    ScenarioNode("acordo_audiencia", 0.35, cash_flow=2_000.0, t_years=5 / 12),
                    ScenarioNode(
                        "merito",
                        0.65,
                        children=[
                            ScenarioNode(
                                "procedencia_3500",
                                0.70,
                                children=[
                                    ScenarioNode(
                                        "sem_recurso", 0.50, cash_flow=3_700.0, t_years=1.2
                                    ),
                                    ScenarioNode(
                                        "recurso_mantido", 0.40, cash_flow=4_000.0, t_years=1.9
                                    ),
                                    ScenarioNode("reformado", 0.10, cash_flow=0.0, t_years=1.9),
                                ],
                            ),
                            ScenarioNode("improcedencia", 0.30, cash_flow=0.0, t_years=1.2),
                        ],
                    ),
                ],
            ),
        ],
    )
    return PricingInputs(
        scenarios=tree.flatten(),
        target_irr=R,
        tax_rate=TAU,
        c_fix=430.0,  # patrocínio automatizado + audiência 400 + preparo esperado 30
        c_serv_pv=90.0,
        face_value=5_000.0,
        reference_value=5_000.0,  # pedido
        label="(iv) voo — pré-ajuizamento",
    )


ALL_EXAMPLES = {
    "consignado_execucao": consignado_execucao,
    "energia_primeira_instancia": energia_primeira_instancia,
    "trabalhista_ro_pendente": trabalhista_ro_pendente,
    "voo_pre_ajuizamento": voo_pre_ajuizamento,
}
