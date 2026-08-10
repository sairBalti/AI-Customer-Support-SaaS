"""LLM client factories."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.domain.interfaces.services.llm_client import LlmClient
from app.infrastructure.llm.fake_client import FakeLlmClient
from app.infrastructure.llm.gemini_client import GeminiLlmClient
from app.infrastructure.llm.openai_client import OpenAILlmClient


def build_llm_client(settings: Settings | None = None) -> LlmClient:
    cfg = settings or get_settings()
    provider = (cfg.llm_provider or "fake").strip().lower()
    if provider in {"fake", "mock", "local", "dev", "hashing"}:
        return FakeLlmClient(model=getattr(cfg, "llm_model", "fake-v1") or "fake-v1")
    if provider == "gemini":
        if not (cfg.gemini_api_key or "").strip():
            # Safe default for local/Docker without paid keys.
            return FakeLlmClient(model="fake-v1")
        return GeminiLlmClient(
            api_key=cfg.gemini_api_key,
            model=getattr(cfg, "llm_model", None) or "gemini-2.0-flash",
        )
    if provider == "openai":
        if not (cfg.openai_api_key or "").strip():
            return FakeLlmClient(model="fake-v1")
        return OpenAILlmClient(api_key=cfg.openai_api_key, model=cfg.llm_model or "gpt-4o-mini")
    raise ValueError(
        f"Unsupported LLM_PROVIDER={cfg.llm_provider!r}. " "Use fake, gemini, or openai."
    )


@lru_cache
def get_llm_client() -> LlmClient:
    return build_llm_client()
