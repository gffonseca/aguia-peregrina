"""N3 — Contrato e assinatura.

Gera o instrumento (cessão, cessão parcial, êxito ou funding) a partir do dossiê e da cotação.
Campos obrigatórios: valor atualizado, líquido estimado, pendências, critério do deságio,
honorários do advogado originário preservados, notificação do devedor (CC 290) e minuta de
habilitação. Assinatura eletrônica via provedor (stub).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

CONTRACT_TYPES = ("cessao", "cessao_parcial", "exito", "funding")
TEMPLATE_VERSION = "2026.10-v1"


@dataclass
class ContractDraft:
    credit_asset_id: uuid.UUID
    pricing_run_id: uuid.UUID | None
    contract_type: str
    price: float
    body_markdown: str
    template_version: str = TEMPLATE_VERSION


def render_contract(
    *,
    credit_asset_id: uuid.UUID,
    pricing_run_id: uuid.UUID | None,
    contract_type: str,
    price: float,
    face_value: float,
    expected_net: float,
    pending_items: list[str],
    lawyer_fee_preserved: bool = True,
) -> ContractDraft:
    if contract_type not in CONTRACT_TYPES:
        raise ValueError(f"tipo inválido: {contract_type}")
    if not lawyer_fee_preserved:
        raise ValueError("honorários do advogado originário devem ser preservados")
    deságio = 1 - (price / face_value) if face_value else 0.0
    body = "\n".join(
        [
            f"# Instrumento de {contract_type} — v{TEMPLATE_VERSION}",
            "",
            f"- Valor de face atualizado: R$ {face_value:,.2f}",
            f"- Líquido estimado ao cessionário: R$ {expected_net:,.2f}",
            f"- Preço: R$ {price:,.2f} (deságio {deságio:.1%}; critério: P_max × margem, "
            "metodologia versionada em pricing_runs)",
            "- Honorários contratuais do advogado originário: preservados (destacados do alvará)",
            "- Notificação ao devedor (CC art. 290): [pendente]",
            "- Habilitação nos autos: minuta anexa",
            "",
            "## Pendências",
            *([f"- {p}" for p in pending_items] or ["- nenhuma"]),
        ]
    )
    return ContractDraft(credit_asset_id, pricing_run_id, contract_type, price, body)


class SignatureProvider:
    """Stub de assinatura eletrônica (Clicksign/Docusign/ZapSign)."""

    def send(self, contract: ContractDraft, signers: list[dict]) -> str:
        return f"stub-{uuid.uuid4()}"
