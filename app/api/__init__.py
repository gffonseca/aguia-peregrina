from fastapi import APIRouter

from app.api import (
    auth,
    cases,
    documents,
    dossiers,
    drafts,
    faturamento,
    fraud,
    integrations,
    jobs,
    ops,
    painel,
    pricing,
    publications,
    reviews,
    subsidies,
    theses,
    triagem,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cases.router)
api_router.include_router(documents.router)
api_router.include_router(subsidies.router)
api_router.include_router(theses.router)
api_router.include_router(fraud.router)
api_router.include_router(dossiers.router)
api_router.include_router(drafts.router)
api_router.include_router(reviews.router)
api_router.include_router(publications.router)
api_router.include_router(pricing.router)
api_router.include_router(integrations.router)
api_router.include_router(ops.router)
api_router.include_router(jobs.router)
api_router.include_router(faturamento.router)
api_router.include_router(painel.router)
api_router.include_router(triagem.router)
