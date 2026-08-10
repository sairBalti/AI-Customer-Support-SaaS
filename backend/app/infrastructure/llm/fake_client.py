"""Deterministic fake LLM for local/CI — never calls paid APIs."""

from __future__ import annotations

from app.domain.interfaces.services.llm_client import LlmChatTurn, LlmGenerationResult


class FakeLlmClient:
    """Grounded mock: summarizes provided context; refuses when context empty."""

    def __init__(self, *, model: str = "fake-v1") -> None:
        self._model = model

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate_response(
        self,
        *,
        system_prompt: str,
        user_message: str,
        context: str,
        history: list[LlmChatTurn] | None = None,
    ) -> LlmGenerationResult:
        _ = system_prompt, history
        cleaned = (context or "").strip()
        if not cleaned:
            answer = (
                "I do not have enough information in the company knowledge base "
                "to answer that question."
            )
        else:
            # Deterministic excerpt used only for tests / offline mode.
            preview = cleaned[:400].strip()
            answer = (
                f"Based on the company knowledge base: {preview}\n\n"
                f"(Responding to: {user_message.strip()[:200]})"
            )
        prompt_tokens = max(1, len(user_message) // 4)
        completion_tokens = max(1, len(answer) // 4)
        return LlmGenerationResult(
            content=answer,
            provider=self.provider_name,
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
