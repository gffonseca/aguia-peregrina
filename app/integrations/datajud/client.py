"""DataJud (CNJ) — API pública Elasticsearch por tribunal. Stub.

Referência: https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal}/_search
Autenticação: header `Authorization: APIKey <chave pública do CNJ>`.
Uso: descoberta de créditos candidatos (autor × réu × classe × movimentos TPU) e jurimetria.
"""

from __future__ import annotations

from typing import Any

import httpx

BASE = "https://api-publica.datajud.cnj.jus.br"


class DataJudClient:
    def __init__(self, api_key: str | None, client: httpx.Client | None = None) -> None:
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=30)

    def search(self, tribunal: str, query: dict[str, Any], size: int = 100) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("DATAJUD_API_KEY ausente")
        url = f"{BASE}/api_publica_{tribunal.lower()}/_search"
        resp = self.client.post(
            url,
            json={"size": size, "query": query},
            headers={"Authorization": f"APIKey {self.api_key}"},
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def by_cnj(cnj_number: str) -> dict[str, Any]:
        return {"match": {"numeroProcesso": cnj_number.replace(".", "").replace("-", "")}}
