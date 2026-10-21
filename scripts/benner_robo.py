#!/usr/bin/env python3
"""Robô do Benner (BASA) — Fase 3, autorizado pelo Banco (autorização arquivada no FBS).

Roda num computador do escritório no Brasil (mesmo esquema do relay do DJEN), com Playwright:
1. entra no Benner com o usuário do escritório (senha lida do Keychain do macOS, serviço
   "aguia-benner", conta = usuário do Benner — cadastrada por quem administra:
       security add-generic-password -a USUARIO_BENNER -s aguia-benner -w );
2. exporta a "Pesquisa de documentos" dos últimos N dias e as fichas (cível e trabalhista);
3. envia para o Águia Peregrina: POST /benner/documentos e POST /faturamento/basa/fichas
   (chave de operação do Keychain, serviço "aguia-ops-key"). O import das fichas confirma
   sozinho as correções já aplicadas no Benner.

Modo diagnóstico (--diag): guarda um print de cada passo em ~/aguia-relay/robo-prints/ para
ajustar seletores se o Benner mudar de tela. Nada é alterado no Benner nesta versão: só leitura
e exportação. Aplicar correções e subir peças entram depois de mapear as telas de edição com
uma ficha de teste indicada pelo escritório.

Instalação (uma vez):  python3 -m pip install --user playwright && python3 -m playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import date, timedelta
from pathlib import Path

BASE = "https://basa.bennercloud.com.br/JURIDICO/"
API = os.environ.get("AGUIA_API", "https://web-production-c2975.up.railway.app")
USUARIO = os.environ.get("BENNER_USUARIO", "")
PASTA = Path.home() / "aguia-relay"
PRINTS = PASTA / "robo-prints"
DOC_INI = "#ctl00_Main_FILTROAVANCADO_EDOCS_FORM_PageControl_GERAL_GERAL_DATAINICIAL_DATE"
DOC_FIM = "#ctl00_Main_FILTROAVANCADO_EDOCS_FORM_PageControl_GERAL_GERAL_DATAFINAL_DATE"
FILTROS_FICHAS = ("Credenciado. Processos Cíveis.", "FONSECA BRASIL TRABALHISTA")


def keychain(servico: str, conta: str) -> str:
    return subprocess.check_output(
        ["security", "find-generic-password", "-a", conta, "-s", servico, "-w"], text=True
    ).strip()


class Robo:
    def __init__(self, page, diag: bool) -> None:  # type: ignore[no-untyped-def]
        self.p = page
        self.diag = diag
        self.n = 0

    def foto(self, nome: str) -> None:
        if self.diag:
            PRINTS.mkdir(parents=True, exist_ok=True)
            self.n += 1
            self.p.screenshot(path=str(PRINTS / f"{self.n:02d}-{nome}.png"), full_page=True)

    def entrar(self, usuario: str, senha: str) -> None:
        self.p.goto(BASE + "Login")
        self.p.fill("#UserName", usuario)
        self.p.fill("#Password", senha)
        self.p.click("#LoginButton")
        self.p.wait_for_load_state("networkidle")
        if "/Login" in self.p.url:
            self.foto("login-falhou")
            raise SystemExit("login recusado pelo Benner (usuário/senha?)")
        self.foto("logado")

    def _bandeja(self, prefixo: str) -> set[str]:
        return set(
            self.p.eval_on_selector_all(
                "a.unread-message.finished",
                f"els=>els.filter(a=>a.textContent.includes({json.dumps(prefixo)})).map(a=>a.href)",
            )
        )

    def _exportar_grid(self, grid_id: str, prefixo: str) -> bytes:
        """Abre o menu do grid, pede 'Exportar para Excel' e espera o arquivo na bandeja."""
        antes = self._bandeja(prefixo)
        menu = self.p.locator(f"[id*='{grid_id}'] .dropdown-toggle").first
        menu.click()
        self.p.locator(
            f"[id*='{grid_id}'] a[title='Exporta os dados do grid para Excel']"
        ).first.click()
        self.foto(f"export-{prefixo}")
        for _ in range(90):  # até 15 min
            time.sleep(10)
            self.p.reload()
            novos = self._bandeja(prefixo) - antes
            if novos:
                url = sorted(novos)[-1]
                r = self.p.request.get(url)
                if r.ok:
                    return r.body()
        raise SystemExit(f"export {prefixo} não terminou em 15 min")

    def documentos(self, dias: int) -> bytes:
        self.p.goto(BASE + "jur/e/FiltroDocumentos/FiltroEspecializadoDocumentos.aspx?p=1")
        hoje = date.today()
        self.p.fill(DOC_INI, (hoje - timedelta(days=dias)).strftime("%d/%m/%Y"))
        self.p.fill(DOC_FIM, hoje.strftime("%d/%m/%Y"))
        self.p.locator("a.btn-save:has-text('Filtrar')").first.click()
        self.p.wait_for_load_state("networkidle")
        self.foto("documentos-filtrado")
        return self._exportar_grid("PR_PROCESSODOCUMENTOS_FILTRO_GRID", "Documentos")

    def fichas(self) -> list[bytes]:
        out = []
        for filtro in FILTROS_FICHAS:
            self.p.goto(BASE)
            self.p.locator("a:text-is('Fichas')").first.click()
            self.p.wait_for_load_state("networkidle")
            self.p.locator(f"text={filtro}").first.click()  # filtro salvo do escritório
            self.p.wait_for_load_state("networkidle")
            self.foto(f"fichas-{filtro[:12]}")
            out.append(self._exportar_grid("PR_PROCESSOS", "Fichas"))
        return out


def enviar(caminho: str, campo: str, arquivos: list[bytes], chave: str) -> str:
    tenant = json.load(urllib.request.urlopen(API + "/auth/tenant", timeout=30))["tenant_id"]
    fronteira = uuid.uuid4().hex
    corpo = b""
    for i, a in enumerate(arquivos):
        corpo += (
            (
                f'--{fronteira}\r\nContent-Disposition: form-data; name="{campo}"; '
                f'filename="robo-{i}.xlsx"\r\nContent-Type: application/octet-stream\r\n\r\n'
            ).encode()
            + a
            + b"\r\n"
        )
    corpo += f"--{fronteira}--\r\n".encode()
    req = urllib.request.Request(
        API + caminho,
        data=corpo,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={fronteira}",
            "X-Ops-Key": chave,
            "X-Tenant-ID": tenant,
            "X-Usuario": "robô Benner",
        },
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read().decode()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--sem-fichas", action="store_true")
    ap.add_argument("--diag", action="store_true")
    ap.add_argument("--visivel", action="store_true", help="abre o navegador na tela")
    a = ap.parse_args()
    if not USUARIO:
        raise SystemExit("defina BENNER_USUARIO (o usuário do Benner, não a senha)")
    from playwright.sync_api import sync_playwright

    senha = keychain("aguia-benner", USUARIO)
    chave = keychain("aguia-ops-key", "aguia")
    with sync_playwright() as pw:
        nav = pw.chromium.launch(headless=not a.visivel)
        page = nav.new_page(accept_downloads=True, viewport={"width": 1500, "height": 900})
        r = Robo(page, a.diag)
        r.entrar(USUARIO, senha)
        docs = r.documentos(a.dias)
        print(
            time.strftime("%Y-%m-%d %H:%M"),
            "documentos:",
            enviar("/benner/documentos", "arquivos", [docs], chave),
        )
        if not a.sem_fichas:
            fx = r.fichas()
            print("fichas:", enviar("/faturamento/basa/fichas", "arquivos", fx, chave))
        nav.close()


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        print("robô:", e, file=sys.stderr)
        raise
