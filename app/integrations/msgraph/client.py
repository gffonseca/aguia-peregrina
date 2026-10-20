"""Leitura de uma caixa do Microsoft 365 via Graph, só leitura (client credentials).

Configuração no Entra ID (feita pelo admin do M365):
- App registration com permissão de aplicação `Mail.Read` (consentimento de admin);
- `New-ApplicationAccessPolicy -AccessRight RestrictAccess` limitando o app à caixa basa@
  (sem isso o app leria todas as caixas do tenant);
- variáveis MSGRAPH_TENANT_ID, MSGRAPH_CLIENT_ID, MSGRAPH_CLIENT_SECRET e TRIAGEM_CAIXA.

O cliente nunca envia, move ou apaga mensagens.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import httpx

from app.modules.m13_triagem.classificar import Email

log = logging.getLogger(__name__)
GRAPH = "https://graph.microsoft.com/v1.0"
_CAMPOS = "id,subject,from,toRecipients,ccRecipients,receivedDateTime,body,webLink,conversationId"


class GraphMailClient:
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        http: httpx.Client | None = None,
    ) -> None:
        self.tenant_id, self.client_id, self.client_secret = tenant_id, client_id, client_secret
        self.http = http or httpx.Client(timeout=60)
        self._token: tuple[str, float] | None = None

    def _bearer(self) -> str:
        if self._token and self._token[1] > time.time():
            return self._token[0]
        r = self.http.post(
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
        )
        r.raise_for_status()
        d = r.json()
        self._token = (d["access_token"], time.time() + int(d.get("expires_in", 3600)) - 120)
        return self._token[0]

    def mensagens(self, caixa: str, desde: datetime) -> Iterator[Email]:
        url: str | None = f"{GRAPH}/users/{caixa}/mailFolders/inbox/messages"
        params: dict[str, Any] | None = {
            "$filter": f"receivedDateTime ge {desde.strftime('%Y-%m-%dT%H:%M:%SZ')}",
            "$orderby": "receivedDateTime asc",
            "$top": "50",
            "$select": _CAMPOS,
        }
        while url:
            r = self.http.get(
                url,
                params=params,
                headers={
                    "Authorization": f"Bearer {self._bearer()}",
                    "Prefer": 'outlook.body-content-type="text"',
                },
            )
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", "10")))
                continue
            r.raise_for_status()
            d = r.json()
            for m in d.get("value", []):
                yield para_email(m)
            url, params = d.get("@odata.nextLink"), None


def _endereco(x: Any) -> str:
    """Aceita o formato do Graph ({emailAddress: {address}}) e o achatado ({address})."""
    if not isinstance(x, dict):
        return str(x or "")
    if isinstance(x.get("emailAddress"), dict):
        return str(x["emailAddress"].get("address", ""))
    return str(x.get("address", ""))


def para_email(m: dict[str, Any]) -> Email:
    """Mensagem do Graph (ou JSON no mesmo formato) → Email da triagem."""
    corpo = m.get("body")
    texto = corpo.get("content", "") if isinstance(corpo, dict) else str(corpo or "")
    return Email(
        id=str(m["id"]),
        remetente=_endereco(m.get("from") or m.get("sender")),
        assunto=m.get("subject") or "",
        corpo=texto or m.get("bodyPreview") or "",
        para=[_endereco(x) for x in m.get("toRecipients") or []],
        cc=[_endereco(x) for x in m.get("ccRecipients") or []],
        recebido_em=m.get("receivedDateTime") or "",
        link=m.get("webLink"),
        conversa=m.get("conversationId"),
    )
