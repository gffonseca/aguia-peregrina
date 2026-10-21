"""Comunica PJe / DJEN (CNJ) — API pública de comunicações processuais (sem chave).

`GET https://comunicaapi.pje.jus.br/api/v1/comunicacao` com filtros `numeroOab` + `ufOab`,
`nomeParte`, `numeroProcesso`, `siglaTribunal`, `dataDisponibilizacaoInicio/Fim` (AAAA-MM-DD),
paginação `pagina` + `itensPorPagina` (até 100). Resposta: `{"count": N, "items": [...]}`; cada
item traz `id`, `data_disponibilizacao`, `siglaTribunal`, `tipoComunicacao`, `nomeOrgao`,
`texto`, `numero_processo`, `numeroprocessocommascara`, `nomeClasse`, `link`, destinatários.

Os nomes de campos variaram entre versões da API; o mapeamento aceita as variantes conhecidas.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any

import httpx

from app.integrations.publications.base import PublicationRecord, PublicationsProvider

BASE_URL = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"
POR_PAGINA = 100
log = logging.getLogger(__name__)


def _primeiro(item: dict[str, Any], *chaves: str) -> Any:
    for k in chaves:
        v = item.get(k)
        if v not in (None, ""):
            return v
    return None


class ComunicaPjeProvider(PublicationsProvider):
    name = "comunica_pje"

    def __init__(self, client: httpx.Client | None = None, pausa_s: float = 0.6) -> None:
        self.client = client or httpx.Client(
            timeout=60, headers={"User-Agent": "aguia-peregrina/fbs (monitoramento DJEN)"}
        )
        self.pausa_s = pausa_s

    def _pagina(self, params: dict[str, Any]) -> dict[str, Any]:
        for tentativa in range(5):
            r = self.client.get(BASE_URL, params=params)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(5 * (tentativa + 1))
                continue
            r.raise_for_status()
            return dict(r.json())
        r.raise_for_status()
        return {}

    def fetch(
        self,
        *,
        since: date,
        oab: str | None = None,
        cnj_numbers: list[str] | None = None,
        nome_parte: str | None = None,
        ate: date | None = None,
        max_paginas: int = 200,
    ) -> list[PublicationRecord]:
        """`oab` no formato '12724/PA'. Sem oab/nome_parte/cnj, não busca (a API exige filtro)."""
        base: dict[str, Any] = {
            "dataDisponibilizacaoInicio": since.isoformat(),
            "dataDisponibilizacaoFim": (ate or date.today()).isoformat(),
            "itensPorPagina": POR_PAGINA,
        }
        consultas: list[dict[str, Any]] = []
        if oab:
            num, _, uf = oab.replace(" ", "").partition("/")
            consultas.append(
                {**base, "numeroOab": "".join(c for c in num if c.isdigit()), "ufOab": uf.upper()}
            )
        if nome_parte:
            consultas.append({**base, "nomeParte": nome_parte})
        for n in cnj_numbers or []:
            consultas.append({**base, "numeroProcesso": "".join(c for c in n if c.isdigit())})
        out: dict[str, PublicationRecord] = {}
        for q in consultas:
            for pagina in range(1, max_paginas + 1):
                d = self._pagina({**q, "pagina": pagina})
                itens = d.get("items") or d.get("itens") or []
                for it in itens:
                    rec = self._map(it)
                    out[rec.provider_ref] = rec
                if len(itens) < POR_PAGINA:
                    break
                time.sleep(self.pausa_s)
        return list(out.values())

    @staticmethod
    def _map(item: dict[str, Any]) -> PublicationRecord:
        num = _primeiro(item, "numero_processo", "numeroProcesso", "numeroprocessocommascara")
        quando = _primeiro(
            item, "data_disponibilizacao", "datadisponibilizacao", "dataDisponibilizacao"
        )
        pub: datetime | None = None
        if quando:
            s = str(quando)
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try:
                    pub = datetime.strptime(s[:10], fmt)
                    break
                except ValueError:
                    continue
        return PublicationRecord(
            provider="comunica_pje",
            provider_ref=str(_primeiro(item, "id", "hash", "numeroComunicacao")),
            cnj_number="".join(c for c in str(num) if c.isdigit()) if num else None,
            published_at=pub,
            text=str(item.get("texto") or ""),
            court=_primeiro(item, "siglaTribunal", "sigla_tribunal"),
            raw=item,
        )
