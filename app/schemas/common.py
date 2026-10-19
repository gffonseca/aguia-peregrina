from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TenantOut(ORMModel):
    id: uuid.UUID
    name: str
    kind: str
    is_active: bool


class Page(BaseModel):
    items: list
    total: int


class Health(BaseModel):
    status: str
    version: str
    env: str
    time: datetime
