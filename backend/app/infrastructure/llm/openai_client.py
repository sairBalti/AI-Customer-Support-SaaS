"""OpenAI LLM adapter placeholder — implement when credentials are configured."""

from __future__ import annotations

from app.domain.interfaces.services.llm_client import LlmChatTurn, LlmGenerationResult


class OpenAILlmClient:
    """Reserved for future OpenAI adapter; not used in local/CI."""

    def __init__(self, *, api_key: str, model: str = "gpt-4o-mini") -> None:
        if not api_key.strip():
            raise ValueError("OPENAI_API_KEY is required for the OpenAI LLM provider.")
        self._model = model

    @property
    def provider_name(self) -> str:
        return "openai"

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
        _ = system_prompt, user_message, context, history
        raise NotImplementedError(
            "OpenAI adapter is not implemented yet. "
            "Use LLM_PROVIDER=fake for local/CI or gemini with GEMINI_API_KEY."
        )
