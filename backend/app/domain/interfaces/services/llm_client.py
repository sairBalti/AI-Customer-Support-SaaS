"""LLM provider port — application must not depend on Gemini/OpenAI SDKs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class LlmChatTurn:
    role: str  # "user" | "assistant"
    content: str


@dataclass(slots=True, frozen=True)
class LlmGenerationResult:
    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


@runtime_checkable
class LlmClient(Protocol):
    """Generate grounded responses from system prompt + context + user message."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    async def generate_response(
        self,
        *,
        system_prompt: str,
        user_message: str,
        context: str,
        history: list[LlmChatTurn] | None = None,
    ) -> LlmGenerationResult: ...
