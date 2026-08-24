"""
Base classes for all agents.

Every agent in the AI Visual Generator workflow inherits from
:class:`AgentBase`.  Two helper dataclasses — :class:`AgentContext` and
:class:`AgentResult` — provide a standard way to pass state between agents
without hard-coding the orchestration logic.
"""

from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.core.exceptions import AgentError
from app.models.schemas import (
    Complexity,
    CriticReport,
    DesignPlan,
    GeneratedImage,
    GenerationStatus,
    ImagePrompt,
    VisualRequest,
    VisualType,
)
from app.providers.text_generator import TextGenerator


# ── Context / Result dataclasses ─────────────────────────────────────────────

@dataclass
class AgentContext:
    """Immutable-ish context object passed between agents.

    Each field is optional; the agent that populates it is responsible for
    setting the corresponding attribute before passing the context on.
    """

    # ── Input ───────────────────────────────────────────────────────────
    request: Optional[VisualRequest] = None

    # ── Intermediate results ────────────────────────────────────────────
    plan: Optional[dict[str, Any]] = None
    design_plan: Optional[DesignPlan] = None
    image_prompt: Optional[ImagePrompt] = None
    generated_image: Optional[GeneratedImage] = None
    critic_report: Optional[CriticReport] = None

    # ── Workflow control ────────────────────────────────────────────────
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    iteration: int = 0
    max_iterations: int = 3
    status: GenerationStatus = GenerationStatus.PENDING

    # ── Arbitrary metadata ──────────────────────────────────────────────
    metadata: dict[str, Any] = field(default_factory=dict)

    def update(self, **kwargs: Any) -> "AgentContext":
        """Return a shallow copy with the given fields updated.

        This keeps the context effectively immutable at the orchestration
        level — agents *can* mutate their local copy but the orchestrator
        always passes a fresh copy forward.
        """
        import copy as _copy
        new = _copy.copy(self)
        for key, value in kwargs.items():
            if hasattr(new, key):
                setattr(new, key, value)
            else:
                new.metadata[key] = value
        return new


@dataclass
class AgentResult:
    """Standard return type for every agent's ``run`` method."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    context_updates: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any = None, **context_updates: Any) -> "AgentResult":
        return cls(success=True, data=data, context_updates=context_updates)

    @classmethod
    def fail(cls, error: str, **context_updates: Any) -> "AgentResult":
        return cls(success=False, error=error, context_updates=context_updates)


# ── Base agent class ─────────────────────────────────────────────────────────

class AgentBase(abc.ABC):
    """Abstract base class for all agents.

    Subclasses implement :meth:`run`, which receives an :class:`AgentContext`
    and returns an :class:`AgentResult`.  The orchestrator is responsible for
    chaining agents together and managing the overall workflow state.
    """

    def __init__(
        self,
        name: str,
        text_generator: TextGenerator | None = None,
    ) -> None:
        self._name: str = name
        self._text_generator: TextGenerator | None = text_generator

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        """Human-readable identifier for this agent."""
        return self._name

    @property
    def text_generator(self) -> TextGenerator | None:
        """Optional text-generation provider used by this agent."""
        return self._text_generator

    @text_generator.setter
    def text_generator(self, value: TextGenerator | None) -> None:
        self._text_generator = value

    @property
    def has_provider(self) -> bool:
        """``True`` if a text-generation provider is attached."""
        return self._text_generator is not None

    # ── Abstract / overridable methods ────────────────────────────────────

    @abc.abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the agent's logic.

        Parameters
        ----------
        context:
            The current :class:`AgentContext` containing all state from
            previous agents.

        Returns
        -------
        AgentResult
            A result object describing whether the agent succeeded and
            providing any data or context updates.
        """
        raise NotImplementedError

    async def health_check(self) -> bool:
        """Return ``True`` if the agent (and its providers) are available."""
        if self._text_generator is not None:
            return await self._text_generator.health_check()
        return True

    # ── Internal helpers ──────────────────────────────────────────────────

    async def _generate_text(self, prompt: str, **kwargs: Any) -> str:
        """Convenience wrapper around the text-generation provider.

        Raises :class:`AgentError` if no provider is configured or generation
        fails.
        """
        if self._text_generator is None:
            raise AgentError(
                f"Agent '{self._name}' has no TextGenerator configured."
            )
        try:
            result = await self._text_generator.generate(prompt, **kwargs)
            return result.text
        except Exception as exc:  # noqa: BLE001 — re-raise as AgentError
            raise AgentError(
                f"Text generation failed in agent '{self._name}': {exc}"
            ) from exc

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self._name!r}>"
