"""
Abstract interface for text-generation providers.

Concrete implementations (OpenAI, Anthropic, Google, local LLM backends, etc.)
subclass :class:`TextGenerator` and implement :meth:`generate` and
:meth:`health_check`.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Optional

from app.providers.base import ProviderConfig
from app.core.exceptions import TextGenerationError


@dataclass
class TextResult:
    """Structured result returned by :meth:`TextGenerator.generate`."""

    text: str
    model: Optional[str] = None
    usage: dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[Any] = None

    @property
    def truncated(self) -> str:
        """Return the text, stripped of leading/trailing whitespace."""
        return self.text.strip()


class TextGenerator(abc.ABC):
    """Abstract base class for all text-generation providers."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config: ProviderConfig = config

    # ── Public API ────────────────────────────────────────────────────────

    @abc.abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> TextResult:
        """Generate text from *prompt*.

        Parameters
        ----------
        prompt:
            The user prompt.
        system_prompt:
            Optional system / instruction prompt.
        temperature:
            Sampling temperature (0 = deterministic).
        max_tokens:
            Maximum tokens to generate.
        **kwargs:
            Provider-specific parameters.

        Returns
        -------
        TextResult
            The generated text and metadata.

        Raises
        ------
        TextGenerationError
            If generation fails for any reason.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return ``True`` when the provider is reachable and authenticated."""
        raise NotImplementedError

    # ── Convenience ───────────────────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return self.config.name

    @property
    def model_name(self) -> Optional[str]:
        return self.config.model
