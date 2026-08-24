"""
Abstract interface for image-generation providers.

Concrete implementations (OpenAI DALL·E, Stability AI, AWS Bedrock, local
Stable Diffusion pipelines, etc.) subclass :class:`ImageGenerator` and
implement :meth:`generate` and :meth:`health_check`.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.providers.base import ProviderConfig
from app.core.exceptions import ImageGenerationError


@dataclass
class ImageResult:
    """Structured result returned by :meth:`ImageGenerator.generate`.

    Either ``image_bytes`` (raw PNG/JPEG bytes) or ``image_path`` (a path
    to a file on disk) will be populated, depending on the provider.
    """

    image_bytes: Optional[bytes] = None
    image_path: Optional[Path] = None
    model: Optional[str] = None
    prompt_used: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[Any] = None

    # ── Convenience ───────────────────────────────────────────────────────

    @property
    def has_data(self) -> bool:
        """``True`` if image bytes or a file path is available."""
        return self.image_bytes is not None or self.image_path is not None

    def to_bytes(self) -> bytes:
        """Return the image as raw bytes, reading from disk if needed."""
        if self.image_bytes is not None:
            return self.image_bytes
        if self.image_path is not None and self.image_path.exists():
            return self.image_path.read_bytes()
        raise ImageGenerationError("No image data available in result.")


class ImageGenerator(abc.ABC):
    """Abstract base class for all image-generation providers."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config: ProviderConfig = config

    # ── Public API ────────────────────────────────────────────────────────

    @abc.abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        width: int | None = None,
        height: int | None = None,
        num_images: int = 1,
        seed: int | None = None,
        **kwargs: Any,
    ) -> ImageResult:
        """Generate an image from *prompt*.

        Parameters
        ----------
        prompt:
            Text prompt describing the desired image.
        width, height:
            Optional dimensions in pixels.
        num_images:
            Number of images to generate (some providers support n>1).
        seed:
            Optional random seed for reproducibility.
        **kwargs:
            Provider-specific parameters.

        Returns
        -------
        ImageResult
            Generated image bytes / path and metadata.

        Raises
        ------
        ImageGenerationError
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
