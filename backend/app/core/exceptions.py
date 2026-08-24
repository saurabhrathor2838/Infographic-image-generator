"""
Custom exception hierarchy for the AI Visual Generator.

Keeping all application errors in one place makes it easy to map them to
HTTP responses or agent-level handling.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application-level errors."""

    def __init__(self, message: str = "", *, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} — {self.details}"
        return self.message or self.__class__.__name__


# ── Provider / infrastructure errors ─────────────────────────────────────────

class ProviderError(AppError):
    """Base class for errors raised by AI / image / storage providers."""


class TextGenerationError(ProviderError):
    """Raised when text generation fails (network, auth, rate-limit, etc.)."""


class ImageGenerationError(ProviderError):
    """Raised when image generation fails."""


class StorageError(ProviderError):
    """Raised when storing or retrieving assets fails."""


# ── Agent errors ─────────────────────────────────────────────────────────────

class AgentError(AppError):
    """Base class for errors raised by agent implementations."""


class PlanningError(AgentError):
    """Raised when the planner / router cannot create a valid plan."""


class DesignError(AgentError):
    """Raised when the design planner fails to produce a design plan."""


class PromptGenerationError(AgentError):
    """Raised when the image-prompt generator fails."""


class CritiqueError(AgentError):
    """Raised when the critic agent cannot evaluate an image."""


class RevisionError(AgentError):
    """Raised when the revision agent cannot improve a generation."""


# ── Orchestration errors ─────────────────────────────────────────────────────

class OrchestrationError(AppError):
    """Raised when the orchestrator encounters an unrecoverable state."""


def error_response(message: str, **kwargs) -> dict:
    """Build a uniform error-response payload for API consumers."""
    payload: dict = {"error": message}
    if kwargs:
        payload["details"] = kwargs
    return payload
