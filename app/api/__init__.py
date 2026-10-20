from fastapi import APIRouter

from app.api import (
    auth,
    cases,
    documents,
    dossiers,
    drafts,
    fraud,
    integrations,
    pricing,
    publications,
    reviews,
    theses,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cases.router)
api_router.include_router(documents.router)
api_router.include_router(theses.router)
api_router.include_router(fraud.router)
api_router.include_router(dossiers.router)
api_router.include_router(drafts.router)
api_router.include_router(reviews.router)
api_router.include_router(publications.router)
api_router.include_router(pricing.router)
api_router.include_router(integrations.router)
