"""Cliente HTTP do Legal One (Thomson Reuters).

Fatos verificados contra o tenant da FBS (2026-10-19):
- OAuth: `GET {LEGALONE_OAUTH}?grant_type=client_credentials` com HTTP Basic
  (client_id:client_secret) → `{access_token, expires_in≈1799}`.
- API OData **somente leitura** em `{LEGALONE_BASE}/{resource}`.
- `$top` máximo 30 (HTTP 400 acima); paginação por `$skip`; `$count` não suportado;
  `$expand=participants` funciona em `lawsuits`, `$expand=updates` não.
- Endpoints de lookup (natures, actiontypes, courts…) respondem 404.

Política de token: cache por `expires_in − 120 s`; em 401 descarta o cache e repete
uma vez; falhas nunca são cacheadas.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator
from typing import Any

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)

MAX_TOP = 30
TOKEN_SAFETY_SECONDS = 120
RETRY_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})

# Recursos conhecidos (confirmados) e lookups (404 no tenant da FBS, mantidos no probe
# para detectar quando passarem a responder).
KNOWN_RESOURCES = ("lawsuits", "contacts", "updates", "tasks", "appointments")
LOOKUP_RESOURCES = ("natures", "actiontypes", "courts", "lawsuitstatuses", "phases")

# Candidatos para descobrir a relação update → lawsuit (nenhum confirmado; ver README).
UPDATE_RELATION_PROBES: tuple[tuple[str, dict[str, str]], ...] = (
    ("lawsuitId", {"$top": "1", "$filter": "lawsuitId gt 0"}),
    ("litigationId", {"$top": "1", "$filter": "litigationId gt 0"}),
    ("relationships", {"$top": "1", "$expand": "relationships"}),
    (
        "relationships/any",
        {"$top": "1", "$filter": "relationships/any(r: r/linkType eq 'Litigation')"},
    ),
)


class LegalOneError(RuntimeError):
    """Erro definitivo (4xx não recuperável, resposta inválida)."""

    def __init__(self, message: str, status_code: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class LegalOneAuthError(LegalOneError):
    """Credenciais ausentes/recusadas."""


class LegalOneUnavailable(LegalOneError):
    """Indisponibilidade após esgotar tentativas (5xx, 429, timeout, rede)."""


class LegalOneClient:
    def __init__(
        self,
        client_id: str | None,
        client_secret: str | None,
        *,
        base: str,
        oauth_url: str,
        http: httpx.Client | None = None,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        timeout: float = 30.0,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.base = base.rstrip("/")
        self.oauth_url = oauth_url
        self.http = http or httpx.Client(timeout=timeout)
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._sleep = sleep
        self._clock = clock
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self.token_requests = 0  # observabilidade/testes

    # ------------------------------------------------------------------ auth
    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def invalidate_token(self) -> None:
        self._token = None
        self._token_expires_at = 0.0

    def token(self, *, force: bool = False) -> str:
        if not self.configured:
            raise LegalOneAuthError("LEGALONE_CLIENT_ID/LEGALONE_CLIENT_SECRET ausentes")
        if not force and self._token and self._clock() < self._token_expires_at:
            return self._token
        self.token_requests += 1
        try:
            resp = self.http.get(
                self.oauth_url,
                params={"grant_type": "client_credentials"},
                auth=(self.client_id or "", self.client_secret or ""),
            )
        except httpx.HTTPError as exc:
            raise LegalOneUnavailable(f"OAuth indisponível: {exc}") from exc
        if resp.status_code in (401, 403):
            raise LegalOneAuthError(
                "credenciais Legal One recusadas", resp.status_code, resp.text[:300]
            )
        if resp.status_code >= 400:
            raise LegalOneUnavailable(
                f"OAuth respondeu {resp.status_code}", resp.status_code, resp.text[:300]
            )
        try:
            data = resp.json()
            access_token = str(data["access_token"])
            expires_in = int(data.get("expires_in") or 1799)
        except (ValueError, KeyError, TypeError) as exc:
            raise LegalOneError("resposta OAuth sem access_token", resp.status_code) from exc
        ttl = max(expires_in - TOKEN_SAFETY_SECONDS, 30)
        self._token = access_token
        self._token_expires_at = self._clock() + ttl
        return access_token

    # ------------------------------------------------------------------- http
    def _url(self, resource: str) -> str:
        return f"{self.base}/{resource.lstrip('/')}"

    def get(self, resource: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET `{base}/{resource}` com token; 401 → renova e repete uma vez; 5xx/429 → backoff."""
        params = dict(params or {})
        if "$top" in params and int(params["$top"]) > MAX_TOP:
            raise ValueError(f"$top máximo é {MAX_TOP} (Legal One devolve 400 acima)")
        retried_auth = False
        attempt = 0
        while True:
            token = self.token()
            try:
                resp = self.http.get(
                    self._url(resource),
                    params=params,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
            except httpx.HTTPError as exc:
                attempt += 1
                if attempt > self.max_retries:
                    raise LegalOneUnavailable(f"falha de rede em {resource}: {exc}") from exc
                self._backoff(attempt)
                continue

            if resp.status_code == 401 and not retried_auth:
                retried_auth = True
                self.invalidate_token()
                continue
            if resp.status_code in RETRY_STATUSES:
                attempt += 1
                if attempt > self.max_retries:
                    raise LegalOneUnavailable(
                        f"{resource} respondeu {resp.status_code} após {self.max_retries} "
                        "tentativas",
                        resp.status_code,
                        resp.text[:300],
                    )
                self._backoff(attempt, resp.headers.get("Retry-After"))
                continue
            if resp.status_code == 401:
                raise LegalOneAuthError("401 após renovar token", 401, resp.text[:300])
            if resp.status_code >= 400:
                raise LegalOneError(
                    f"{resource} respondeu {resp.status_code}", resp.status_code, resp.text[:300]
                )
            try:
                data = resp.json()
            except ValueError as exc:
                raise LegalOneError(f"{resource}: resposta não é JSON", resp.status_code) from exc
            if isinstance(data, list):  # alguns endpoints devolvem lista crua
                return {"value": data}
            if not isinstance(data, dict):
                raise LegalOneError(f"{resource}: JSON inesperado", resp.status_code)
            return data

    def _backoff(self, attempt: int, retry_after: str | None = None) -> None:
        delay = self.backoff_seconds * (2 ** (attempt - 1))
        if retry_after:
            try:
                delay = max(delay, float(retry_after))
            except ValueError:
                pass
        log.warning("legalone: tentativa %s, aguardando %.1fs", attempt, delay)
        self._sleep(delay)

    def iterate(
        self,
        resource: str,
        params: dict[str, Any] | None = None,
        *,
        page_size: int = MAX_TOP,
        max_pages: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Pagina com `$top`/`$skip` até página vazia/curta ou `max_pages`."""
        if page_size < 1 or page_size > MAX_TOP:
            raise ValueError(f"page_size deve estar entre 1 e {MAX_TOP}")
        base_params = dict(params or {})
        page = 0
        skip = 0
        while max_pages is None or page < max_pages:
            data = self.get(resource, {**base_params, "$top": page_size, "$skip": skip})
            items = data.get("value")
            if not isinstance(items, list):
                raise LegalOneError(f"{resource}: payload sem 'value'")
            for item in items:
                if isinstance(item, dict):
                    yield item
            page += 1
            if len(items) < page_size:
                break
            skip += page_size

    # ------------------------------------------------------------------ probe
    def probe(self) -> dict[str, Any]:
        """Verifica quais recursos respondem (sem gravar nada). Útil para ops e para
        descobrir, no tenant real, como `updates` se relaciona com `lawsuits`."""
        out: dict[str, Any] = {"configured": self.configured, "resources": {}, "lookups": {}}
        if not self.configured:
            return out
        try:
            self.token()
            out["oauth"] = "ok"
        except LegalOneError as exc:
            out["oauth"] = f"erro: {exc}"
            return out

        def _try(resource: str, params: dict[str, Any]) -> dict[str, Any]:
            try:
                data = self.get(resource, params)
                items = data.get("value") or []
                first = items[0] if items and isinstance(items[0], dict) else {}
                return {"status": "ok", "fields": sorted(first.keys())[:60]}
            except LegalOneError as exc:
                return {"status": f"erro {exc.status_code or ''}".strip(), "detail": str(exc)}

        for r in KNOWN_RESOURCES:
            out["resources"][r] = _try(r, {"$top": 1})
        for r in LOOKUP_RESOURCES:
            out["lookups"][r] = _try(r, {"$top": 1})
        out["update_relation"] = {
            name: _try("updates", params) for name, params in UPDATE_RELATION_PROBES
        }
        return out


def get_legalone_client(http: httpx.Client | None = None) -> LegalOneClient:
    s = get_settings()
    return LegalOneClient(
        s.legalone_client_id,
        s.legalone_client_secret,
        base=s.legalone_base,
        oauth_url=s.legalone_oauth,
        http=http,
    )


__all__ = [
    "KNOWN_RESOURCES",
    "LOOKUP_RESOURCES",
    "MAX_TOP",
    "LegalOneAuthError",
    "LegalOneClient",
    "LegalOneError",
    "LegalOneUnavailable",
    "get_legalone_client",
]
