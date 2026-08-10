"""Gemini LLM adapter (optional). Requires GEMINI_API_KEY when selected."""

from __future__ import annotations

import httpx

from app.domain.interfaces.services.llm_client import LlmChatTurn, LlmGenerationResult


class GeminiLlmClient:
    """Thin REST adapter for Google Gemini generateContent."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-2.0-flash",
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key.strip():
            raise ValueError("GEMINI_API_KEY is required for the Gemini LLM provider.")
        self._api_key = api_key.strip()
        self._model = model
        self._timeout = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "gemini"

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
        contents: list[dict[str, object]] = []
        for turn in history or []:
            role = "user" if turn.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": turn.content}]})
        user_block = (
            f"Knowledge context:\n{context or '(none)'}\n\n"
            f"Customer question:\n{user_message.strip()}"
        )
        contents.append({"role": "user", "parts": [{"text": user_block}]})

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                url,
                params={"key": self._api_key},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        text = ""
        candidates = data.get("candidates") or []
        if candidates:
            parts = (((candidates[0] or {}).get("content") or {}).get("parts")) or []
            text = "".join(str(p.get("text") or "") for p in parts if isinstance(p, dict))
        usage = data.get("usageMetadata") or {}
        return LlmGenerationResult(
            content=text.strip() or "I was unable to generate a response.",
            provider=self.provider_name,
            model=self.model_name,
            prompt_tokens=int(usage.get("promptTokenCount") or 0),
            completion_tokens=int(usage.get("candidatesTokenCount") or 0),
        )
