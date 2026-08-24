"""
Abstract interface for storage providers.

Concrete implementations (local filesystem, S3, GCS, Azure Blob, etc.)
subclass :class:`StorageProvider` and implement :meth:`save`,
:meth:`retrieve`, :meth:`delete`, and :meth:`health_check`.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional

from app.providers.base import ProviderConfig
from app.core.exceptions import StorageError


@dataclass
class StorageResult:
    """Information returned after saving or retrieving an asset."""

    path: str
    url: Optional[str] = None
    metadata: dict | None = None


class StorageProvider(abc.ABC):
    """Abstract base class for all storage providers."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config: ProviderConfig = config

    # ── Public API ────────────────────────────────────────────────────────

    @abc.abstractmethod
    async def save(
        self,
        data: bytes,
        filename: str,
        *,
        content_type: str | None = None,
        **kwargs,
    ) -> StorageResult:
        """Persist *data* (raw bytes) under *filename*.

        Returns a :class:`StorageResult` with the storage path and optional URL.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def retrieve(self, path: str) -> bytes:
        """Retrieve and return raw bytes stored at *path*."""
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete the object at *path*.  Returns ``True`` on success."""
        raise NotImplementedError

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return ``True`` when storage is reachable."""
        raise NotImplementedError

    # ── Convenience ───────────────────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return self.config.name
