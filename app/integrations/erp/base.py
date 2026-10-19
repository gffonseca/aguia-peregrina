"""Conector de ERP do cliente (TOTVS, Projuris, Preâmbulo, CSV). Write-back de resultado."""

from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from typing import Any

from app.models.litigation import Outcome


class ErpConnector(ABC):
    name: str

    def serialize_outcome(self, outcome: Outcome) -> dict[str, Any]:
        return {
            "case_id": str(outcome.case_id),
            "stage": outcome.stage,
            "result": outcome.result,
            "award_value": outcome.award_value,
            "decided_at": outcome.decided_at.isoformat() if outcome.decided_at else None,
            "reason": outcome.reason,
        }

    @abstractmethod
    def send(self, payload: dict[str, Any]) -> str:
        """Envia e devolve referência externa."""


class CsvExportConnector(ErpConnector):
    """Fallback universal: gera linha CSV para importação periódica no ERP do cliente."""

    name = "csv"

    def send(self, payload: dict[str, Any]) -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(payload))
        writer.writeheader()
        writer.writerow(payload)
        return buf.getvalue()
