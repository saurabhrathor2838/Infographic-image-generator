"""
Provider factories.

These build concrete providers from the application settings.  Each factory is
a plain function so it can be used both directly (by the orchestrator) and as
a FastAPI dependency (``Depends(get_text_generator)``) which makes the
providers trivially overridable in tests via ``app.dependency_overrides``.

No API keys live here — values are read from :class:`app.core.config.settings`,
which itself is populated from environment variables / ``.env``.
"""

from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.providers.base import ProviderConfig
from app.providers.openai_text_generator import OpenAITextGenerator
from app.providers.text_generator import TextGenerator


def create_provider_config(provider: str, model: Optional[str]) -> ProviderConfig:
    """Build a :class:`ProviderConfig` from the shared application settings."""
    return ProviderConfig(
        name=provider,
        api_key=settings.openai_api_key if provider == "openai" else None,
        base_url=None,
        model=model,
    )


def text_generator_from_settings() -> Optional[TextGenerator]:
    """Construct a text generator based on ``settings.ai_provider``.

    Returns ``None`` when no provider / key is configured, allowing callers to
    degrade gracefully (e.g. the mocked Phase 1 path).
    """
    provider = (settings.ai_provider or "").strip().lower()
    if provider == "openai" and settings.openai_api_key:
        return OpenAITextGenerator(
            create_provider_config(provider, settings.text_model)
        )
    return None


def get_text_generator() -> Optional[TextGenerator]:
    """FastAPI dependency returning the configured text generator.

    Override in tests with ``app.dependency_overrides[get_text_generator]``.
    """
    return text_generator_from_settings()


# Convenience alias for the image provider (Phase 4 — not yet implemented).
def get_image_generator() -> Optional["object"]:  # noqa: D401
    """Placeholder image-generator dependency (returns ``None`` for now)."""
    return None
