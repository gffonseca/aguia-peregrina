"""CLI do motor de oportunidades (arquivos locais; em produção o worker usa `servico.py`).

python -m app.modules.m12_faturamento.oportunidades_cli \\
    --movimentos raw.jsonl --prestacoes jul.xlsx ago.xlsx set.xlsx \\
    --benner Fichas.xlsx ... --hoje 2026-10-20 --cobertura 2026-07-01:2026-09-30 --saida out.xlsx

`--cobertura` = período coberto pelas prestações informadas. Eventos cuja janela cai dentro
dele são conciliados (ATENDIDA/PERDIDA); os posteriores entram na fila (ABERTA).
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.modules.m12_faturamento.deteccao import unir_graus
from app.modules.m12_faturamento.planilhas import ler_atos, ler_benner
from app.modules.m12_faturamento.relatorio import gerar_relatorio, selecionar
from app.modules.m12_faturamento.tabela import reconhecer_ato


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _dig(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


def executar(
    movimentos: Path,
    prestacoes: list[Path],
    benner: list[Path],
    hoje: date,
    cobertura: tuple[date, date],
    saida: Path,
) -> dict[str, Any]:
    docs = [json.loads(linha) for linha in movimentos.read_text(encoding="utf-8").splitlines()]
    processos = unir_graus(docs)
    fichas = {_dig(f.cnj): f.ficha for f in ler_benner(benner).values()} if benner else {}
    cobrados: dict[str, list[tuple[date, str]]] = defaultdict(list)
    for p in prestacoes:
        for ln in ler_atos(p):
            a = reconhecer_ato(ln.ato_texto)
            if a and ln.data:
                cobrados[_dig(ln.cnj)].append((ln.data, a))
    ops = selecionar(processos.values(), cobrados, hoje, cobertura)
    xlsx, resumo = gerar_relatorio(ops, len(processos), fichas, hoje, cobertura)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_bytes(xlsx)
    return resumo


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--movimentos", required=True, type=Path)
    ap.add_argument("--prestacoes", nargs="*", default=[], type=Path)
    ap.add_argument("--benner", nargs="*", default=[], type=Path)
    ap.add_argument("--hoje", default=date.today().isoformat())
    ap.add_argument("--cobertura", required=True, help="AAAA-MM-DD:AAAA-MM-DD")
    ap.add_argument("--saida", required=True, type=Path)
    a = ap.parse_args()
    ini, fim = (_d(x) for x in a.cobertura.split(":"))
    r = executar(a.movimentos, a.prestacoes, a.benner, _d(a.hoje), (ini, fim), a.saida)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
