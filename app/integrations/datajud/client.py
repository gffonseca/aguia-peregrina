"""DataJud (CNJ) — API pública Elasticsearch, um índice por tribunal.

Referência: https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal}/_search
Autenticação: header `Authorization: APIKey <chave>`. A chave pública é divulgada pelo CNJ
(datajud-wiki.cnj.jus.br/api-publica/acesso) e pode mudar: `DATAJUD_API_KEY` substitui o padrão.

O índice devolve um documento por grau (G1, G2, JE, TR...). `buscar_por_numeros` consulta em
lotes de até 100 números e, com `desde`, só o que foi atualizado a partir daquela data.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Iterator
from datetime import datetime
from typing import Any

import httpx

from app.core import cnj as cnjlib

BASE = "https://api-publica.datajud.cnj.jus.br"
log = logging.getLogger(__name__)

# J.TR → alias do índice. Cobre a carteira BASA (AM/PA) e vizinhos; demais caem em None.
_ALIAS: dict[tuple[int, int], str] = {
    (8, 14): "tjpa",
    (8, 4): "tjam",
    (8, 1): "tjac",
    (8, 3): "tjap",
    (8, 22): "tjro",
    (8, 23): "tjrr",
    (8, 27): "tjto",
    (8, 10): "tjma",
    (8, 11): "tjmt",
    (8, 9): "tjgo",
    (8, 18): "tjpi",
    (8, 20): "tjrn",
    (8, 21): "tjrs",
    (8, 26): "tjsp",
    (8, 19): "tjrj",
    (8, 7): "tjdft",
    (8, 13): "tjmg",
    (8, 5): "tjba",
    (8, 6): "tjce",
    (8, 17): "tjpe",
    (5, 8): "trt8",
    (5, 11): "trt11",
    (5, 14): "trt14",
    (5, 16): "trt16",
    (4, 1): "trf1",
}


def alias_do_tribunal(numero: str) -> str | None:
    p = cnjlib.parse(numero)
    if p is None:
        return None
    return _ALIAS.get((p.segment, p.tribunal))


class DataJudClient:
    def __init__(
        self,
        api_key: str | None,
        client: httpx.Client | None = None,
        pausa_erro_s: float = 5.0,
    ) -> None:
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=90)
        self.pausa_erro_s = pausa_erro_s

    def search(self, tribunal: str, query: dict[str, Any], size: int = 100) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("DATAJUD_API_KEY ausente")
        url = f"{BASE}/api_publica_{tribunal.lower()}/_search"
        ultimo: Exception | None = None
        for tentativa in range(5):
            try:
                resp = self.client.post(
                    url,
                    json={"size": size, "query": query},
                    headers={"Authorization": f"APIKey {self.api_key}"},
                )
                resp.raise_for_status()
                return dict(resp.json())
            except (httpx.HTTPError, ValueError) as e:  # 429/5xx/timeouts: tenta de novo
                ultimo = e
                log.warning("datajud %s tentativa %s: %s", tribunal, tentativa + 1, e)
                time.sleep(self.pausa_erro_s * (tentativa + 1))
        raise RuntimeError(f"DataJud {tribunal}: {ultimo}")

    def buscar_por_numeros(
        self,
        tribunal: str,
        numeros: Iterable[str],
        desde: datetime | None = None,
        lote: int = 100,
    ) -> Iterator[dict[str, Any]]:
        """Devolve os hits (`_id` + `_source`) dos números informados (só dígitos)."""
        nums = list(dict.fromkeys(numeros))
        for i in range(0, len(nums), lote):
            filtros: list[dict[str, Any]] = [{"terms": {"numeroProcesso": nums[i : i + lote]}}]
            if desde is not None:
                filtros.append(
                    {
                        "range": {
                            "dataHoraUltimaAtualizacao": {
                                "gte": desde.strftime("%Y-%m-%dT%H:%M:%S")
                            }
                        }
                    }
                )
            r = self.search(tribunal, {"bool": {"filter": filtros}}, size=lote * 5)
            yield from r.get("hits", {}).get("hits", [])

    @staticmethod
    def by_cnj(cnj_number: str) -> dict[str, Any]:
        return {"match": {"numeroProcesso": cnj_number.replace(".", "").replace("-", "")}}
