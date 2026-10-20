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
from concurrent.futures import ThreadPoolExecutor
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
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="aguia-job")

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

    def dispatch_async(self, job_name: str, payload: dict[str, Any]) -> str:
        """Executa o job em thread própria e devolve a referência na hora.

        Necessário para jobs longos (dossiê/minuta levam minutos): o proxy do Railway
        encerra requisições HTTP em ~5 min. O cliente consulta `GET /jobs/{ref}`.
        """
        fn = self._jobs[job_name]
        ref = f"inproc-{next(self._counter)}"
        self._results[ref] = {"status": "running", "job": job_name}

        def _run() -> None:
            try:
                result = fn(payload)
                self._results[ref] = {"status": "done", "job": job_name, "result": result}
            except Exception as exc:  # noqa: BLE001 - o erro vai para quem consulta o job
                log.exception("job %s (%s) falhou", job_name, ref)
                self._results[ref] = {"status": "failed", "job": job_name, "error": str(exc)}
            self.history.append((job_name, payload, self._results[ref]))

        self._executor.submit(_run)
        return ref

    def result_for(self, ref: str) -> dict[str, Any] | None:
        """Resultado síncrono de um job (só faz sentido no engine in_process)."""
        return self._results.get(ref)

    def job_status(self, ref: str) -> dict[str, Any] | None:
        """Estado de um job assíncrono: running | done | failed (ou None se desconhecido)."""
        entry = self._results.get(ref)
        if entry is None:
            return None
        if "status" in entry and entry.get("job"):
            return entry
        return {"status": "done", "result": entry}


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
