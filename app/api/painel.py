"""Páginas estáticas de operação. Não trazem dados: a página pede a chave de operação e chama
a API com ela (os endpoints continuam protegidos por X-Ops-Key)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["painel"])
_DIR = Path(__file__).parent
_HEADERS = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex"}


@router.get("/painel/recebiveis", response_class=HTMLResponse, include_in_schema=False)
def painel_recebiveis() -> HTMLResponse:
    return HTMLResponse((_DIR / "painel_recebiveis.html").read_text("utf-8"), headers=_HEADERS)


@router.get("/painel/triagem", response_class=HTMLResponse, include_in_schema=False)
def painel_triagem() -> HTMLResponse:
    return HTMLResponse((_DIR / "painel_triagem.html").read_text("utf-8"), headers=_HEADERS)
