from __future__ import annotations

from dataclasses import dataclass, field

REQUIRED_BY_TYPOLOGY: dict[str, list[str]] = {
    "consignado": ["contrato", "extrato", "comprovante_credito", "documento_pessoal"],
    "energia": ["fatura", "historico_consumo", "ordem_servico", "registro_interrupcao"],
    "voo": ["bilhete", "registro_voo", "comunicacao_passageiro", "comprovante_reacomodacao"],
    "trabalhista": ["contrato_trabalho", "ponto", "holerites", "trct"],
}


@dataclass
class SubsidyChecklist:
    typology: str
    present: set[str] = field(default_factory=set)

    @property
    def missing(self) -> list[str]:
        return [k for k in REQUIRED_BY_TYPOLOGY.get(self.typology, []) if k not in self.present]

    @property
    def complete(self) -> bool:
        return not self.missing


def build_checklist(typology: str, available_kinds: set[str]) -> SubsidyChecklist:
    """Regra determinística de 'falta X' por tipologia."""
    return SubsidyChecklist(typology=typology, present=set(available_kinds))
