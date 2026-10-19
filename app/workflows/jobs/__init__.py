from __future__ import annotations

from app.workflows.engine import WorkflowEngine
from app.workflows.jobs import (
    build_dossier,
    generate_draft,
    intake_publication,
    monitor_publication,
    pricing_run,
    process_document,
)

JOBS = {
    "intake_publication": intake_publication.run,
    "process_document": process_document.run,
    "build_dossier": build_dossier.run,
    "generate_draft": generate_draft.run,
    "monitor_publication": monitor_publication.run,
    "pricing_run": pricing_run.run,
}


def register_all(engine: WorkflowEngine) -> None:
    for name, fn in JOBS.items():
        engine.register(name, fn)
