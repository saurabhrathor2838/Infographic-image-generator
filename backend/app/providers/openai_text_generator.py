"""
Concrete text-generation provider backed by the OpenAI Chat Completions API.

Uses :mod:`httpx` (already a project dependency) directly rather than the
``openai`` SDK, keeping the dependency surface minimal while remaining fully
compatible with the project's existing HTTP/async stack.

Configuration is supplied through :class:`~app.providers.base.ProviderConfig`,
which is populated from environment variables by the application settings — no
API keys are ever hard-coded in this module.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

from app.core.exceptions import TextGenerationError
from app.providers.base import ProviderConfig
from app.providers.text_generator import TextGenerator, TextResult

# Default OpenAI endpoint.  Overridable per-instance via ``config.base_url``.
DEFAULT_BASE_URL: str = "https://api.openai.com/v1"


class OpenAITextGenerator(TextGenerator):
    """Text generator backed by ``POST /v1/chat/completions``."""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config=config)
        if not self.config.api_key:
            raise ValueError(
                "OpenAITextGenerator requires a non-empty api_key in its config."
            )
        self._base_url: str = (
            self.config.base_url or DEFAULT_BASE_URL
        ).rstrip("/")
        self._model: str = self.config.model or "gpt-4o-mini"
        self._timeout: float = 60.0

    # ── Public API ────────────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> TextResult:
        """Call the OpenAI chat-completions endpoint and return the reply."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout
            ) as client:
                resp = await client.post(
                    "/chat/completions", json=payload, headers=headers
                )
        except httpx.HTTPError as exc:
            raise TextGenerationError(
                f"OpenAI request failed: {exc}"
            ) from exc

        if resp.status_code != 200:
            raise TextGenerationError(
                f"OpenAI API error {resp.status_code}: {resp.text}"
            )

        try:
            data = resp.json()
        except ValueError as exc:  # malformed JSON
            raise TextGenerationError(
                f"OpenAI returned non-JSON: {exc}"
            ) from exc

        if not data.get("choices"):
            raise TextGenerationError(
                "OpenAI response contained no choices."
            )

        content: str = data["choices"][0]["message"]["content"]
        return TextResult(
            text=content,
            model=self._model,
            usage=data.get("usage", {}),
            raw_response=data,
        )

    async def health_check(self) -> bool:
        """Return ``True`` if the key is accepted by the OpenAI API."""
        if not self.config.api_key:
            return False
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=10.0
            ) as client:
                resp = await client.get("/models", headers=headers)
            return resp.status_code == 200
        except Exception:
            return False

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return "openai"
