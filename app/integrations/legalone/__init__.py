"""Legal One (Thomson Reuters) — conector OData somente leitura.

- `client.py`: OAuth client_credentials, GET com retry/backoff, paginação `$top/$skip` (máx. 30).
- `sync.py`: sync incremental processos → cases, participantes → case_parties, contatos →
  clients, andamentos → publications, tarefas → legalone_records (sem tabela de prazos ainda).
- `app/core/cnj.py`: decodifica tribunal/segmento/foro do número CNJ (lookups da API dão 404).

Protocolo/peticionamento continua manual no Legal One até validarmos endpoints de escrita.
"""

from app.integrations.legalone.client import (
    LegalOneAuthError,
    LegalOneClient,
    LegalOneError,
    LegalOneUnavailable,
    get_legalone_client,
)

__all__ = [
    "LegalOneAuthError",
    "LegalOneClient",
    "LegalOneError",
    "LegalOneUnavailable",
    "get_legalone_client",
]
