"""Páginas estáticas de operação. Não trazem dados: a página pede a chave de operação e chama
a API com ela (os endpoints continuam protegidos por X-Ops-Key)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

router = APIRouter(tags=["painel"])
_DIR = Path(__file__).parent
_HEADERS = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex"}


@router.get("/painel/recebiveis", response_class=HTMLResponse, include_in_schema=False)
def painel_recebiveis() -> HTMLResponse:
    return HTMLResponse((_DIR / "painel_recebiveis.html").read_text("utf-8"), headers=_HEADERS)


@router.get("/painel/triagem", response_class=HTMLResponse, include_in_schema=False)
def painel_triagem() -> HTMLResponse:
    return HTMLResponse((_DIR / "painel_triagem.html").read_text("utf-8"), headers=_HEADERS)


@router.get("/painel/oportunidades", response_class=HTMLResponse, include_in_schema=False)
def painel_oportunidades() -> HTMLResponse:
    return HTMLResponse((_DIR / "painel_oportunidades.html").read_text("utf-8"), headers=_HEADERS)


@router.get("/painel/correcoes", response_class=HTMLResponse, include_in_schema=False)
def painel_correcoes() -> HTMLResponse:
    return HTMLResponse((_DIR / "painel_correcoes.html").read_text("utf-8"), headers=_HEADERS)


@router.get("/painel/entrar", response_class=HTMLResponse, include_in_schema=False)
def painel_entrar() -> HTMLResponse:
    return HTMLResponse((_DIR / "painel_entrar.html").read_text("utf-8"), headers=_HEADERS)


@router.get("/painel/sessao.js", include_in_schema=False)
def painel_sessao() -> Response:
    return Response(
        (_DIR / "painel_sessao.js").read_text("utf-8"),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/painel/gestao", response_class=HTMLResponse, include_in_schema=False)
def painel_gestao() -> HTMLResponse:
    return HTMLResponse((_DIR / "painel_gestao.html").read_text("utf-8"), headers=_HEADERS)
