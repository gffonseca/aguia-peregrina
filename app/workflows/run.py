"""Executa um job pelo nome, no processo atual (operações/manutenção).

    python -m app.workflows.run sync_legalone --tenant-id <uuid> --since 2026-10-01 --max-pages 50
    python -m app.workflows.run sync_legalone --since auto --resources lawsuits,updates

Sem `--tenant-id`, usa o único tenant `law_firm` ativo (erro se houver mais de um).
`--dispatch` envia para a engine de workflows (Hatchet, se configurado) em vez de rodar aqui.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models.tenant import Tenant
from app.workflows.jobs import JOBS


def _resolve_tenant_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    with SessionLocal() as db:
        tenants = list(db.scalars(select(Tenant).where(Tenant.is_active.is_(True))))
    firms = [t for t in tenants if t.kind == "law_firm"] or tenants
    if len(firms) != 1:
        raise SystemExit(
            f"--tenant-id obrigatório ({len(firms)} tenants ativos: "
            + ", ".join(f"{t.name}={t.id}" for t in firms)
            + ")"
        )
    return str(firms[0].id)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m app.workflows.run")
    p.add_argument("job", choices=sorted(JOBS))
    p.add_argument("--tenant-id")
    p.add_argument("--since", help="YYYY-MM-DD, 'auto' (última execução ok) ou omitido = tudo")
    p.add_argument("--max-pages", type=int)
    p.add_argument("--resources", help="lista separada por vírgula (ex.: lawsuits,updates)")
    p.add_argument("--payload", help="JSON extra mesclado ao payload do job")
    p.add_argument("--dispatch", action="store_true", help="enfileira na engine em vez de rodar")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=get_settings().log_level)
    payload: dict[str, Any] = {"tenant_id": _resolve_tenant_id(args.tenant_id)}
    if args.since:
        payload["since"] = args.since
    if args.max_pages:
        payload["max_pages"] = args.max_pages
    if args.resources:
        payload["resources"] = [r.strip() for r in args.resources.split(",") if r.strip()]
    if args.payload:
        payload.update(json.loads(args.payload))

    if args.dispatch:
        from app.workflows.engine import get_engine

        ref = get_engine().dispatch(args.job, payload)
        print(json.dumps({"dispatched": args.job, "ref": ref}, ensure_ascii=False))
        return 0
    result = JOBS[args.job](payload)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
