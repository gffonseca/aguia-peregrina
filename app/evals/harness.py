"""Esqueleto de eval: dataset JSONL de casos rotulados → roda tarefa → métricas.

Formato do dataset (uma linha por item):
  {"id": "...", "task": "page_type|extraction|dossier|draft", "input": {...}, "expected": {...}}
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

Scorer = Callable[[Any, Any], float]


@dataclass
class EvalItem:
    id: str
    task: str
    input: dict[str, Any]
    expected: Any


@dataclass
class EvalReport:
    task: str
    n: int
    mean_score: float
    per_item: list[tuple[str, float]] = field(default_factory=list)


def load_jsonl(path: Path) -> list[EvalItem]:
    items: list[EvalItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            items.append(EvalItem(d["id"], d["task"], d["input"], d["expected"]))
    return items


def exact_match(pred: Any, expected: Any) -> float:
    return 1.0 if pred == expected else 0.0


def run_eval(
    items: Iterable[EvalItem], runner: Callable[[dict[str, Any]], Any], scorer: Scorer = exact_match
) -> EvalReport:
    rows: list[tuple[str, float]] = []
    task = ""
    for it in items:
        task = it.task
        rows.append((it.id, scorer(runner(it.input), it.expected)))
    mean = sum(s for _, s in rows) / len(rows) if rows else float("nan")
    return EvalReport(task, len(rows), mean, rows)
