from app.integrations.publications.base import PublicationRecord, PublicationsProvider
from app.integrations.publications.comunica_pje import ComunicaPjeProvider
from app.integrations.publications.solucionare import SolucionareProvider


def get_publications_provider(name: str) -> PublicationsProvider:
    if name == "comunica_pje":
        return ComunicaPjeProvider()
    if name == "solucionare":
        return SolucionareProvider()
    raise ValueError(f"provider desconhecido: {name}")


__all__ = [
    "ComunicaPjeProvider",
    "PublicationRecord",
    "PublicationsProvider",
    "SolucionareProvider",
    "get_publications_provider",
]
