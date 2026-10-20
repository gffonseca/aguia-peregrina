"""Adaptador de engine de workflows.

Interface mínima: registrar jobs e disparar por nome com payload serializável.
- `HatchetEngine`: usa hatchet-sdk (extra `workflows`), com HATCHET_CLIENT_TOKEN.
- `InProcessEngine`: executa síncrono no mesmo processo (dev/testes).
"""

from __future__ import annotations

import itertools
import logging
from collections import deque
from collections.abc import Callable
from typing import Any, Protocol

from app.core.config import get_settings

log = logging.getLogger(__name__)

JobFn = Callable[[dict[str, Any]], dict[str, Any]]


class WorkflowEngine(Protocol):
    name: str

    def register(self, job_name: str, fn: JobFn) -> None: ...

    def dispatch(self, job_name: str, payload: dict[str, Any]) -> str: ...


class InProcessEngine:
    name = "in_process"

    def __init__(self) -> None:
        self._jobs: dict[str, JobFn] = {}
        # histórico limitado (processo web de longa duração) e resultado por referência
        self.history: deque[tuple[str, dict[str, Any], dict[str, Any]]] = deque(maxlen=200)
        self._results: dict[str, dict[str, Any]] = {}
        self._counter = itertools.count(1)

    def register(self, job_name: str, fn: JobFn) -> None:
        self._jobs[job_name] = fn

    def dispatch(self, job_name: str, payload: dict[str, Any]) -> str:
        fn = self._jobs[job_name]
        ref = f"inproc-{next(self._counter)}"
        result = fn(payload)
        self.history.append((job_name, payload, result))
        self._results[ref] = result
        if len(self._results) > 500:
            for old in list(self._results)[:-200]:
                self._results.pop(old, None)
        return ref

    def result_for(self, ref: str) -> dict[str, Any] | None:
        """Resultado síncrono de um job (só faz sentido no engine in_process)."""
        return self._results.get(ref)


class HatchetEngine:
    name = "hatchet"

    def __init__(self) -> None:
        try:
            from hatchet_sdk import Hatchet  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "hatchet-sdk não instalado (pip install 'aguia-peregrina[workflows]')"
            ) from exc
        self.hatchet = Hatchet()
        self._jobs: dict[str, JobFn] = {}
        self._workflows: dict[str, Any] = {}

    def register(self, job_name: str, fn: JobFn) -> None:
        self._jobs[job_name] = fn
        wf = self.hatchet.workflow(name=job_name)

        @wf.task()
        def _run(input: Any, ctx: Any) -> dict[str, Any]:  # pragma: no cover - roda no worker
            data = input if isinstance(input, dict) else getattr(input, "model_dump", lambda: {})()
            return fn(data)

        self._workflows[job_name] = wf

    def dispatch(self, job_name: str, payload: dict[str, Any]) -> str:
        ref = self._workflows[job_name].run_no_wait(payload)
        return str(getattr(ref, "workflow_run_id", ref))

    def worker(self) -> Any:  # pragma: no cover
        worker = self.hatchet.worker("aguia-worker", workflows=list(self._workflows.values()))
        return worker


_engine: WorkflowEngine | None = None


def get_engine() -> WorkflowEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        if settings.workflow_engine == "hatchet" and settings.hatchet_client_token:
            _engine = HatchetEngine()
        else:
            if settings.workflow_engine == "hatchet":
                log.warning("WORKFLOW_ENGINE=hatchet sem token; usando in_process")
            _engine = InProcessEngine()
        from app.workflows.jobs import register_all

        register_all(_engine)
    return _engine
