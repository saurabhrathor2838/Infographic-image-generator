"""
Provider package for the AI Visual Generator.

Sub-modules:
  - base:               shared ``BaseProvider`` and ``ProviderConfig``
  - text_generator:     ``TextGenerator`` abstract interface
  - image_generator:    ``ImageGenerator`` abstract interface
  - storage_provider:   ``StorageProvider`` abstract interface
"""

from app.providers.base import BaseProvider, ProviderConfig
from app.providers.text_generator import TextGenerator, TextResult
from app.providers.image_generator import ImageGenerator, ImageResult
from app.providers.storage_provider import StorageProvider, StorageResult

__all__ = [
    "BaseProvider",
    "ProviderConfig",
    "TextGenerator",
    "TextResult",
    "ImageGenerator",
    "ImageResult",
    "StorageProvider",
    "StorageResult",
]
