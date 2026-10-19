"""Gateway de LLM (LiteLLM) com log obrigatório em `llm_calls`."""

from app.llm.client import LLMClient, LLMResponse, get_llm_client

__all__ = ["LLMClient", "LLMResponse", "get_llm_client"]
