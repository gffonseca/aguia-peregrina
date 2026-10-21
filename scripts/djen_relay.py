#!/usr/bin/env python3
"""Relay do DJEN (Comunica PJe) para o Águia Peregrina.

A API do DJEN só responde a IPs do Brasil; o servidor fica nos EUA. Este script roda num
computador do escritório no Brasil (launchd, a cada 3 h), busca os últimos 3 dias e envia os
itens crus para POST /triagem/intimacoes/importar. Só biblioteca padrão do Python.

A chave de operação NÃO fica neste arquivo: é lida do Keychain do macOS
(serviço "aguia-ops-key"), cadastrada por quem administra com:
    security add-generic-password -a aguia -s aguia-ops-key -w
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

API = os.environ.get("AGUIA_API", "https://web-production-c2975.up.railway.app")
DJEN = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"
NOME_PARTE = os.environ.get("DJEN_NOME_PARTE", "BANCO DA AMAZONIA")
OABS = [x.strip() for x in os.environ.get("DJEN_OABS", "12724/PA").split(",") if x.strip()]
DIAS = int(os.environ.get("DJEN_DIAS", "3"))


def chave() -> str:
    return subprocess.check_output(
        ["security", "find-generic-password", "-a", "aguia", "-s", "aguia-ops-key", "-w"], text=True
    ).strip()


def get(url: str) -> dict:
    for tentativa in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "aguia-relay/fbs"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if tentativa == 4:
                raise
            print("djen: nova tentativa", e, file=sys.stderr)
            time.sleep(5 * (tentativa + 1))
    return {}


def buscar(filtro: dict[str, str]) -> list[dict]:
    hoje = date.today()
    base = {
        "dataDisponibilizacaoInicio": (hoje - timedelta(days=DIAS)).isoformat(),
        "dataDisponibilizacaoFim": hoje.isoformat(),
        "itensPorPagina": "100",
        **filtro,
    }
    itens: list[dict] = []
    for pagina in range(1, 201):
        d = get(DJEN + "?" + urllib.parse.urlencode({**base, "pagina": str(pagina)}))
        lote = d.get("items") or []
        itens += lote
        if len(lote) < 100:
            break
        time.sleep(0.6)
    return itens


def main() -> None:
    k = chave()
    tenant = json.load(urllib.request.urlopen(API + "/auth/tenant", timeout=30))["tenant_id"]
    corpo = {
        "por_parte": buscar({"nomeParte": NOME_PARTE}) if NOME_PARTE else [],
        "por_oab": [
            i
            for oab in OABS
            for i in buscar(
                {
                    "numeroOab": oab.split("/")[0].replace(".", ""),
                    "ufOab": oab.split("/")[1].upper(),
                }
            )
        ],
    }
    req = urllib.request.Request(
        API + "/triagem/intimacoes/importar",
        data=json.dumps(corpo).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Ops-Key": k,
            "X-Tenant-ID": tenant,
            "X-Usuario": "relay DJEN",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        print(time.strftime("%Y-%m-%d %H:%M"), r.read().decode())


if __name__ == "__main__":
    main()
