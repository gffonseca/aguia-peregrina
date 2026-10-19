from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str
    tenant_id: uuid.UUID


class MfaIn(BaseModel):
    token: str
    code: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    mfa_required: bool = False
