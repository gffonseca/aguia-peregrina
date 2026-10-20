"""Páginas estáticas de operação. Não trazem dados: a página pede a chave de operação e chama
a API com ela (os endpoints continuam protegidos por X-Ops-Key)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["painel"])
_HTML = Path(__file__).with_name("painel_recebiveis.html")


@router.get("/painel/recebiveis", response_class=HTMLResponse, include_in_schema=False)
def painel_recebiveis() -> HTMLResponse:
    return HTMLResponse(
        _HTML.read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"},
    )
