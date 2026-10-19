"""Solucionare (ou Judit/Escavador) — provedor pago com webhook. Stub."""

from __future__ import annotations

from datetime import date

from app.integrations.publications.base import PublicationRecord, PublicationsProvider


class SolucionareProvider(PublicationsProvider):
    name = "solucionare"

    def fetch(
        self, *, since: date, oab: str | None = None, cnj_numbers: list[str] | None = None
    ) -> list[PublicationRecord]:
        return []

    def parse_webhook(self, payload: dict) -> list[PublicationRecord]:
        items = payload.get("publicacoes", [])
        return [
            PublicationRecord(
                provider=self.name,
                provider_ref=str(i.get("id")),
                cnj_number=i.get("processo"),
                published_at=None,
                text=i.get("conteudo", ""),
                raw=i,
            )
            for i in items
        ]
