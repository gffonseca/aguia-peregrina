"""Entrypoint do processo `worker` (Procfile/Railway)."""

from __future__ import annotations

import logging
import time

from app.core.config import get_settings
from app.workflows.engine import HatchetEngine, get_engine

log = logging.getLogger("aguia.worker")


def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    engine = get_engine()
    if isinstance(engine, HatchetEngine):  # pragma: no cover
        log.info("iniciando worker Hatchet")
        engine.worker().start()
        return
    log.warning("engine in_process: worker ocioso (jobs rodam no processo web). Ctrl+C para sair.")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
