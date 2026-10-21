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
ajustar seletores se o Benner mudar de tela.

Correções (--aplicar N): pega até N itens que um advogado LIBEROU no painel (status "aprovado",
com os parâmetros que só ele decide) e, para cada um, abre a ficha e:
- SITUACAO → Encerramento: Editar, "Encerrado", data, motivo, êxito, Salvar, confere;
- SUBIR_PECA → Documentos: Novo, data, nome, tipo, arquivo (baixado do Águia), Salvar, confere.
Sem --confirmar é SIMULAÇÃO: preenche tudo, tira print e CANCELA (nada é gravado). Com
--confirmar grava e marca o item "feito" (por "robô Benner"); o export seguinte confirma.
Erro num item: cancela, devolve o item para "pendente" com o motivo e segue para o próximo.
Telas mapeadas em 20/10/2026 na ficha CIVE.005182/2020 (sem gravar).

Instalação (uma vez):  python3 -m pip install --user playwright && python3 -m playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
GRID_FICHAS = "jur/a/PR_PROCESSOS/Grid.aspx?i=PR_PROCESSOS_MENU&m=MAIN"
FILTRO_FICHA = "#ctl00_Main_K9_PASTAS_FilterControl_GERAL_PROCESSO"
ENC = "ctl00_Main_PR_PROCESSOS_FORM_PageControl_ENCERRAMENTO_ENCERRAMENTO_"
DOC = "ctl00_Main_PR_PROCESSODOCUMENTOS_FORM_PageControl_GERAL_GERAL_"
# rádio "Situação": 1 Em andamento, 2 Encerrado, 3 Cumprindo acordo, 4 Em encerramento,
# 5 Em reativação (só no modo edição), 6 Baixa provisória, 7 Reativação de baixa provisória
SIT_ANDAMENTO, SIT_ENCERRADO = "1", "2"
EXITO = {"sim": "1", "nao": "2"}


class Falha(Exception):
    """Erro num item: o robô cancela a edição e segue para o próximo."""


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

    # ---------------- correções (Fase 3) ----------------
    def _espera(self) -> None:
        self.p.wait_for_load_state("networkidle")
        self.p.wait_for_timeout(600)

    def abrir_ficha(self, ficha: str) -> None:
        self.p.goto(BASE + GRID_FICHAS)
        self._espera()
        campo = self.p.locator(FILTRO_FICHA)
        campo.fill(ficha)
        campo.press("Enter")
        self._espera()
        link = self.p.locator("table tbody a", has_text=ficha).first
        if link.count() == 0:
            raise Falha(f"ficha {ficha} não encontrada no grid")
        link.click()
        self._espera()
        if ficha not in self.p.locator(".page-breadcrumb, .breadcrumb").first.inner_text():
            raise Falha("a tela aberta não é a ficha pedida")

    def _radio(self, prefixo: str, valor: str):  # type: ignore[no-untyped-def]
        return self.p.locator(f"input[type=radio][id^='{prefixo}'][value='{valor}']").first

    def _marcar_radio(self, prefixo: str, valor: str) -> None:
        r = self._radio(prefixo, valor)
        rid = r.get_attribute("id")
        lab = self.p.locator(f"label[for='{rid}']")
        (lab if lab.count() else r).first.click(force=True)
        self._espera()

    def _select2(self, raiz, select_css: str, texto: str) -> None:  # type: ignore[no-untyped-def]
        """Campos de busca do Benner (select2 com carga por ajax): digita e escolhe o exato."""
        raiz.locator(select_css).locator("xpath=following-sibling::span[1]").click()
        busca = raiz.locator(".select2-container--open .select2-search__field").first
        busca.fill(texto)
        self.p.wait_for_timeout(1500)
        opc = raiz.locator(".select2-results__option").filter(
            has_text=re.compile(rf"^\s*{re.escape(texto)}\s*$", re.I)
        )
        if opc.count() == 0:
            busca.press("Escape")
            raise Falha(f"opção '{texto}' não existe na lista do Benner")
        opc.first.click()
        self.p.wait_for_timeout(500)

    def _erros(self, raiz) -> str:  # type: ignore[no-untyped-def]
        txt = raiz.locator(
            ".alert-danger:visible, .validation-summary:visible, .has-error .help-block:visible"
        )
        return " | ".join(t.strip() for t in txt.all_inner_texts() if t.strip())[:400]

    def encerrar(self, ficha: str, prm: dict, confirmar: bool) -> str:
        self.abrir_ficha(ficha)
        self.p.locator(".nav-tabs a", has_text="Encerramento").first.click()
        self._espera()
        if not self._radio(ENC + "SITUACAO_ctl", SIT_ANDAMENTO).is_checked():
            raise Falha("a ficha já não está 'Em andamento' no Benner (nada a fazer)")
        self.p.locator("a.btn-edit:visible").first.click()
        self._espera()
        self._marcar_radio(ENC + "SITUACAO_ctl", SIT_ENCERRADO)
        data = self.p.locator(f"#{ENC}SITUACAO_2_DATAENCERRAMENTO_DATE")
        data.fill(prm["data"])
        data.press("Tab")
        self._select2(self.p, f"select[id^='{ENC}SITUACAO_2_'][id$='_select']", prm["motivo"])
        self._marcar_radio(ENC + "SITUACAO_2_EXITO_ctl", EXITO[prm["exito"]])
        self.foto(f"encerrar-{ficha.replace('/', '_')}-preenchido")
        if not confirmar:
            self.p.locator("a.btn-cancel:visible").first.click()
            self._espera()
            return "simulado (cancelado, nada gravado)"
        self.p.locator("a.btn-save:visible").first.click()
        self._espera()
        erro = self._erros(self.p)
        if erro or self.p.locator("a.btn-save:visible").count():
            self.foto(f"encerrar-{ficha.replace('/', '_')}-erro")
            if self.p.locator("a.btn-cancel:visible").count():
                self.p.locator("a.btn-cancel:visible").first.click()
            raise Falha("o Benner não aceitou: " + (erro or "formulário continuou em edição"))
        self.p.locator(".nav-tabs a", has_text="Encerramento").first.click()
        if not self._radio(ENC + "SITUACAO_ctl", SIT_ENCERRADO).is_checked():
            raise Falha("salvou, mas a ficha não aparece como Encerrado")
        self.foto(f"encerrar-{ficha.replace('/', '_')}-gravado")
        return "encerrada"

    def subir_peca(self, ficha: str, prm: dict, arquivo: Path, confirmar: bool) -> str:
        self.abrir_ficha(ficha)
        novo = self.p.locator("#ctl00_Main_DOCUMENTOS2_toolbar a.btn-new")
        if not novo.is_visible():
            self.p.locator("#portlet_DOCUMENTOS2 .caption").first.click()  # grade recolhida
            self._espera()
        antes = self.p.locator("#portlet_DOCUMENTOS2 tbody tr", has_text=prm["nome"]).count()
        novo.click()
        self.p.wait_for_selector("iframe")
        self.p.wait_for_timeout(1500)
        fr = next(f for f in self.p.frames if "PR_PROCESSODOCUMENTOS/Form.aspx" in f.url)
        fr.wait_for_load_state("networkidle")
        d = fr.locator(f"#{DOC}DATADOCUMENTO_DATE")
        d.fill(prm["data"])
        d.press("Tab")
        fr.locator(f"#{DOC}NOME").fill(prm["nome"])
        # 1º select de busca do formulário = "Tipo documento"; o 2º é "Pasta virtual"
        self._select2(fr, f"select[id^='{DOC}'][id$='_select'] >> nth=0", prm["tipo"])
        fr.locator("input[type=file]").first.set_input_files(str(arquivo))
        fr.wait_for_load_state("networkidle")
        self.p.wait_for_timeout(2500)  # upload do arquivo
        self.foto(f"peca-{ficha.replace('/', '_')}-preenchido")
        if not confirmar:
            fr.locator("a.btn-cancel").first.click()
            self._espera()
            return "simulado (cancelado, nada gravado)"
        fr.locator("a.btn-save").first.click()
        self.p.wait_for_timeout(3000)
        self._espera()
        if any("PR_PROCESSODOCUMENTOS/Form.aspx" in f.url for f in self.p.frames):
            fr2 = next(f for f in self.p.frames if "PR_PROCESSODOCUMENTOS/Form.aspx" in f.url)
            erro = self._erros(fr2)
            if erro or fr2.locator("a.btn-save:visible").count():
                self.foto(f"peca-{ficha.replace('/', '_')}-erro")
                fr2.locator("a.btn-cancel").first.click()
                raise Falha("o Benner não aceitou o documento: " + (erro or "modal ficou aberto"))
        depois = self.p.locator("#portlet_DOCUMENTOS2 tbody tr", has_text=prm["nome"]).count()
        if depois <= antes:
            raise Falha("salvou, mas o documento não apareceu na grade da ficha")
        self.foto(f"peca-{ficha.replace('/', '_')}-gravado")
        return "peça incluída"


def api_json(caminho: str, chave: str, metodo: str = "GET", corpo: dict | None = None) -> dict:
    tenant = json.load(urllib.request.urlopen(API + "/auth/tenant", timeout=30))["tenant_id"]
    req = urllib.request.Request(
        API + caminho,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        method=metodo,
        headers={
            "Content-Type": "application/json",
            "X-Ops-Key": chave,
            "X-Tenant-ID": tenant,
            "X-Usuario": "robô Benner",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        bruto = r.read()
    return json.loads(bruto) if bruto[:1] in (b"{", b"[") else {"_bytes": bruto}


def aplicar(r: Robo, chave: str, limite: int, confirmar: bool) -> None:
    fila = api_json(f"/benner/correcoes/robo?limite={limite}", chave)["itens"]
    print(f"{len(fila)} item(ns) liberado(s) — {'GRAVANDO' if confirmar else 'SIMULAÇÃO'}")
    PASTA.mkdir(parents=True, exist_ok=True)
    for it in fila:
        prm, ficha = it["parametros"] or {}, it["ficha"]
        try:
            if it["tipo"] == "SITUACAO":
                res = r.encerrar(ficha, prm, confirmar)
            elif it["tipo"] == "SUBIR_PECA":
                dados = api_json(f"/benner/correcoes/{it['id']}/anexo", chave)["_bytes"]
                arq = PASTA / "pecas" / it["anexo_nome"]
                arq.parent.mkdir(parents=True, exist_ok=True)
                arq.write_bytes(dados)
                res = r.subir_peca(ficha, prm, arq, confirmar)
            else:
                continue
            print(f"  {ficha} {it['tipo']}: {res}")
            if confirmar:
                api_json(
                    f"/benner/correcoes/{it['id']}",
                    chave,
                    "PATCH",
                    {"status": "feito", "observacao": f"robô: {res}"},
                )
        except Falha as e:
            print(f"  {ficha} {it['tipo']}: FALHOU — {e}", file=sys.stderr)
            if confirmar or "já não está" in str(e):
                api_json(
                    f"/benner/correcoes/{it['id']}",
                    chave,
                    "PATCH",
                    {"status": "pendente", "observacao": f"robô não aplicou: {e}"[:2000]},
                )


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
    ap.add_argument(
        "--aplicar",
        type=int,
        default=0,
        metavar="N",
        help="aplica até N correções liberadas no painel (sem exportar nada)",
    )
    ap.add_argument(
        "--confirmar",
        action="store_true",
        help="com --aplicar: grava no Benner (sem isto é simulação)",
    )
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
        if a.aplicar:
            aplicar(r, chave, a.aplicar, a.confirmar)
            nav.close()
            return
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
