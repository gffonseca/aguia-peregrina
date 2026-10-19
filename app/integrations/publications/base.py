from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class PublicationRecord:
    provider: str
    provider_ref: str
    cnj_number: str | None
    published_at: datetime | None
    text: str
    court: str | None = None
    raw: dict | None = None


class PublicationsProvider(ABC):
    name: str

    @abstractmethod
    def fetch(
        self, *, since: date, oab: str | None = None, cnj_numbers: list[str] | None = None
    ) -> list[PublicationRecord]:
        """Busca publicações desde `since`, por OAB do escritório ou lista de processos."""

    def parse_webhook(self, payload: dict) -> list[PublicationRecord]:
        raise NotImplementedError(f"{self.name} não suporta webhook")
