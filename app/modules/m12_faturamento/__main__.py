"""CLI da pré-auditoria e do Anexo II.

python -m app.modules.m12_faturamento ATOS.xlsx --competencia 2026-07 \\
    [--benner Fichas.xlsx ...] --saida OUT.xlsx
"""

from __future__ import annotations

import argparse
import json

from app.modules.m12_faturamento.auditoria import auditar
from app.modules.m12_faturamento.planilhas import gerar_excel, ler_atos, ler_benner


def main() -> None:
    p = argparse.ArgumentParser(description="Pré-auditoria e Anexo II do contrato BASA FB1798")
    p.add_argument("atos", help="planilha de atos praticados no mês (.xlsx)")
    p.add_argument("--competencia", required=True, help="AAAA-MM")
    p.add_argument("--benner", nargs="*", default=[], help="exports Fichas.xlsx do Benner")
    p.add_argument("--saida", required=True, help="arquivo .xlsx de saída")
    a = p.parse_args()
    linhas = ler_atos(a.atos)
    benner = ler_benner(a.benner) if a.benner else None
    rs = gerar_excel(auditar(linhas, a.competencia, benner), a.competencia, a.saida)
    print(json.dumps(rs, ensure_ascii=False, indent=2, default=float))


if __name__ == "__main__":
    main()
