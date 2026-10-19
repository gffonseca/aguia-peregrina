from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.litigation import GtTask


def sample(
    entity_ids: list[uuid.UUID], share: float = 0.1, seed: int | None = None
) -> list[uuid.UUID]:
    rng = random.Random(seed)
    k = max(1, int(len(entity_ids) * share)) if entity_ids else 0
    return rng.sample(entity_ids, k)


def open_task(
    db: Session, *, tenant_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID, model_answer: dict
) -> GtTask:
    task = GtTask(
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        sampled_at=datetime.now(UTC),
        model_answer=model_answer,
    )
    db.add(task)
    return task


def agreement(a: dict, b: dict) -> float:
    """Concordância simples por chave; substituir por métrica por tipo de tarefa."""
    keys = set(a) | set(b)
    if not keys:
        return 1.0
    return sum(1 for k in keys if a.get(k) == b.get(k)) / len(keys)
