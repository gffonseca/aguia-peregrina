"""M3 Subsídios — vínculo processo ↔ registro interno do cliente e checklist de faltantes.

Os subsídios chegam do cliente (ERP/contrato/logs) como campos de origem `subsidio` do
playbook e ficam em `cases.meta["subsidios"]`; o checklist determinístico cruza o que o
playbook exige com o que já está nos autos (tipos de página do M2) e nos subsídios.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.litigation import Case, Document, DocumentPage
from app.modules.m02_autos.service import evidence_kinds_from_page_types

REQUIRED_BY_TYPOLOGY: dict[str, list[str]] = {
    "consignado": ["contrato", "extrato", "comprovante_credito", "documento_pessoal"],
    "energia": ["fatura", "historico_consumo", "ordem_servico", "registro_interrupcao"],
    "voo": ["bilhete", "registro_voo", "comunicacao_passageiro", "comprovante_reacomodacao"],
    "trabalhista": ["contrato_trabalho", "ponto", "holerites", "trct"],
}

SUBSIDIES_KEY = "subsidios"


def typology_family(typology: str | None) -> str:
    """`consignado_rmc_nao_reconhecido` → `consignado`."""
    if not typology:
        return ""
    for fam in REQUIRED_BY_TYPOLOGY:
        if typology == fam or typology.startswith(fam + "_"):
            return fam
    return typology


@dataclass
class SubsidyChecklist:
    typology: str
    present: set[str] = field(default_factory=set)
    required: list[str] = field(default_factory=list)

    @property
    def missing(self) -> list[str]:
        req = self.required or REQUIRED_BY_TYPOLOGY.get(typology_family(self.typology), [])
        return [k for k in req if k not in self.present]

    @property
    def complete(self) -> bool:
        return not self.missing


def build_checklist(
    typology: str, available_kinds: set[str], required: list[str] | None = None
) -> SubsidyChecklist:
    """Regra determinística de 'falta X' por tipologia."""
    return SubsidyChecklist(
        typology=typology, present=set(available_kinds), required=list(required or [])
    )


def set_subsidies(db: Session, *, case: Case, data: dict[str, Any], replace: bool = False) -> dict:
    """Grava/mescla os campos de subsídio vindos do cliente em `cases.meta.subsidios`."""
    meta = dict(case.meta or {})
    current = {} if replace else dict(meta.get(SUBSIDIES_KEY) or {})
    current.update(data)
    meta[SUBSIDIES_KEY] = current
    case.meta = meta
    db.add(case)
    return current


def get_subsidies(case: Case) -> dict[str, Any]:
    return dict((case.meta or {}).get(SUBSIDIES_KEY) or {})


def page_types_for_case(db: Session, case_id: uuid.UUID) -> list[str]:
    rows = db.execute(
        select(DocumentPage.page_type)
        .join(Document, Document.id == DocumentPage.document_id)
        .where(Document.case_id == case_id)
    ).all()
    return [r[0] for r in rows if r[0]]


def checklist_for_case(
    db: Session, *, case: Case, required: list[str] | None = None
) -> SubsidyChecklist:
    kinds = evidence_kinds_from_page_types(page_types_for_case(db, case.id))
    subs = get_subsidies(case)
    # subsídios declarados pelo cliente contam como presentes quando apontam documento juntável
    if subs.get("ted_comprovante_localizado") is True:
        kinds |= {"comprovante_ted", "comprovante_credito"}
    if subs.get("contrato_localizado") is True:
        kinds.add("contrato")
    if subs.get("ip_log_disponivel") is True:
        kinds.add("log_autenticacao")
    return build_checklist(case.typology or "", kinds, required)


__all__ = [
    "REQUIRED_BY_TYPOLOGY",
    "SUBSIDIES_KEY",
    "SubsidyChecklist",
    "build_checklist",
    "checklist_for_case",
    "get_subsidies",
    "page_types_for_case",
    "set_subsidies",
    "typology_family",
]
