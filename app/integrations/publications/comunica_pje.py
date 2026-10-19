"""Comunica PJe / DJEN (CNJ) — API pública de comunicações processuais.

Endpoint de referência: https://comunicaapi.pje.jus.br/api/v1/comunicacao
Parâmetros usuais: numeroOab, ufOab, siglaTribunal, dataDisponibilizacaoInicio/Fim, numeroProcesso.
Stub: sem chamada real; implementar com httpx e paginação.
"""

from __future__ import annotations

from datetime import date

import httpx

from app.integrations.publications.base import PublicationRecord, PublicationsProvider

BASE_URL = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"


class ComunicaPjeProvider(PublicationsProvider):
    name = "comunica_pje"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client

    def fetch(
        self, *, since: date, oab: str | None = None, cnj_numbers: list[str] | None = None
    ) -> list[PublicationRecord]:
        # TODO: implementar paginação real. Mantido como stub para o esqueleto.
        return []

    @staticmethod
    def _map(item: dict) -> PublicationRecord:
        return PublicationRecord(
            provider="comunica_pje",
            provider_ref=str(item.get("id") or item.get("hash")),
            cnj_number=item.get("numero_processo") or item.get("numeroprocessocommascara"),
            published_at=None,
            text=item.get("texto", ""),
            court=item.get("siglaTribunal"),
            raw=item,
        )
