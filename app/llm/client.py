"""Wrapper sobre LiteLLM.

- `litellm` é dependência opcional (extra `llm`); sem ela o cliente funciona em modo `fake`
  (útil em testes e CI), devolvendo respostas determinísticas.
- Toda chamada grava um `LlmCall` com model, prompt_hash, tokens, latency e custo; o prompt em
  claro nunca é persistido.
- `structured()` força saída JSON validada por um schema pydantic.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings

litellm: Any
try:  # dependência opcional (extra `llm`)
    import litellm  # type: ignore[import-not-found,no-redef]

    LITELLM_AVAILABLE = True
except Exception:  # pragma: no cover - ambiente sem litellm
    litellm = None
    LITELLM_AVAILABLE = False

T = TypeVar("T", bound=BaseModel)


@functools.lru_cache(maxsize=1)
def _model_catalog() -> dict[str, dict[str, Any]]:
    """Lê `model_list` do litellm_config.yaml → {nome_lógico: litellm_params}."""
    path = Path(get_settings().litellm_config)
    if not path.is_absolute():
        # procura a partir da raiz do pacote e do cwd
        for base in (Path(__file__).resolve().parents[2], Path.cwd()):
            if (base / path).exists():
                path = base / path
                break
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 - catálogo ausente → sem alias
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in data.get("model_list", []) or []:
        name = item.get("model_name")
        params = item.get("litellm_params") or {}
        if name and params.get("model"):
            out[str(name)] = dict(params)
    return out


@dataclass
class LLMResponse:
    content: str
    model: str
    provider_model: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    cost_usd: float | None
    llm_call_id: uuid.UUID | None = None
    raw: Any = field(default=None, repr=False)


def prompt_hash(messages: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


class LLMClient:
    def __init__(self, *, fake: bool | None = None) -> None:
        self.settings = get_settings()
        if fake is None:
            mode = self.settings.llm_mode
            if mode == "fake":
                fake = True
            elif mode == "live":
                fake = False
            else:
                fake = not LITELLM_AVAILABLE
        self.fake = fake

    # ------------------------------------------------------------------ core
    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        purpose: str,
        db: Session | None = None,
        tenant_id: uuid.UUID | None = None,
        case_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        model: str | None = None,
        prompt_version: str | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        model = model or self.settings.llm_default_model
        p_hash = prompt_hash(messages)
        started = time.perf_counter()
        status, error = "ok", None
        try:
            if self.fake:
                resp = self._fake_response(messages, model, response_format)
            else:
                resp = self._litellm_response(messages, model, response_format, **kwargs)
        except Exception as exc:
            status, error = "error", str(exc)
            resp = LLMResponse("", model, None, None, None, 0, None)
            raise
        finally:
            resp_latency = int((time.perf_counter() - started) * 1000)
            if db is not None and tenant_id is not None:
                resp.llm_call_id = self._log(
                    db,
                    tenant_id=tenant_id,
                    purpose=purpose,
                    model=model,
                    provider_model=resp.provider_model,
                    p_hash=p_hash,
                    prompt_version=prompt_version,
                    input_tokens=resp.input_tokens,
                    output_tokens=resp.output_tokens,
                    latency_ms=resp_latency,
                    cost_usd=resp.cost_usd,
                    status=status,
                    error=error,
                    case_id=case_id,
                    user_id=user_id,
                )
        resp.latency_ms = resp_latency
        return resp

    def structured(
        self,
        messages: list[dict[str, Any]],
        schema: type[T],
        *,
        purpose: str,
        max_retries: int = 1,
        **kwargs: Any,
    ) -> tuple[T, LLMResponse]:
        """Saída estruturada: pede JSON conforme o schema e valida com pydantic."""
        schema_json = schema.model_json_schema()
        sys_msg = {
            "role": "system",
            "content": "Responda SOMENTE com JSON válido conforme o schema: "
            + json.dumps(schema_json, ensure_ascii=False),
        }
        attempt = 0
        last_err: Exception | None = None
        while attempt <= max_retries:
            resp = self.complete(
                [sys_msg, *messages],
                purpose=purpose,
                response_format={"type": "json_object"},
                **kwargs,
            )
            try:
                return schema.model_validate_json(_strip_fences(resp.content)), resp
            except ValidationError as exc:
                last_err = exc
                attempt += 1
        raise ValueError(
            f"saída estruturada inválida após {max_retries + 1} tentativas: {last_err}"
        )

    # ---------------------------------------------------------------- backends
    def _litellm_response(
        self,
        messages: list[dict[str, Any]],
        model: str,
        response_format: dict[str, Any] | None,
        **kwargs: Any,
    ) -> LLMResponse:
        assert litellm is not None
        params: dict[str, Any] = {"model": model, "messages": messages, **kwargs}
        if response_format:
            params["response_format"] = response_format
        if self.settings.litellm_proxy_url:
            params["api_base"] = self.settings.litellm_proxy_url
            params["api_key"] = self.settings.litellm_proxy_key
            params["model"] = f"openai/{model}"  # proxy expõe interface OpenAI-compatível
        else:
            # Sem proxy: resolve o nome lógico (claude-sonnet) para o modelo do vendor
            # usando o catálogo do litellm_config.yaml, e injeta a chave do ambiente.
            alias = _model_catalog().get(model)
            if alias:
                params["model"] = alias["model"]
                for key in ("max_tokens", "temperature"):
                    if key in alias and key not in params:
                        params[key] = alias[key]
                api_key_ref = alias.get("api_key", "")
                if isinstance(api_key_ref, str) and api_key_ref.startswith("os.environ/"):
                    env_val = os.environ.get(api_key_ref.split("/", 1)[1])
                    if env_val:
                        params["api_key"] = env_val
        out = litellm.completion(**params)
        usage = getattr(out, "usage", None)
        cost = None
        try:
            cost = litellm.completion_cost(completion_response=out)
        except Exception:  # noqa: BLE001
            cost = None
        return LLMResponse(
            content=out.choices[0].message.content or "",
            model=model,
            provider_model=getattr(out, "model", None),
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            latency_ms=0,
            cost_usd=cost,
            raw=out,
        )

    def _fake_response(
        self, messages: list[dict[str, Any]], model: str, response_format: dict[str, Any] | None
    ) -> LLMResponse:
        content = "{}" if response_format else "[fake] " + messages[-1].get("content", "")[:80]
        return LLMResponse(content, model, f"fake/{model}", 10, 5, 0, 0.0)

    def _log(self, db: Session, **fields: Any) -> uuid.UUID:
        from app.models.litigation import LlmCall

        row = LlmCall(
            tenant_id=fields["tenant_id"],
            purpose=fields["purpose"],
            model=fields["model"],
            provider_model=fields["provider_model"],
            prompt_hash=fields["p_hash"],
            prompt_version=fields["prompt_version"],
            input_tokens=fields["input_tokens"],
            output_tokens=fields["output_tokens"],
            latency_ms=fields["latency_ms"],
            cost_usd=fields["cost_usd"],
            status=fields["status"],
            error=fields["error"],
            case_id=fields["case_id"],
            user_id=fields["user_id"],
        )
        db.add(row)
        db.flush()
        return row.id


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
