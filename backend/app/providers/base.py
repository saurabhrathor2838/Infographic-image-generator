"""
Shared base classes and configuration for all providers.

This module defines :class:`ProviderConfig` (a common configuration container)
and :class:`BaseProvider` (the abstract root all provider types inherit from).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ProviderConfig:
    """Common configuration passed to every provider implementation."""

    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


class BaseProvider(abc.ABC):
    """Abstract base class shared by all provider types.

    Concrete providers must implement :meth:`health_check`.  They may also
    override :attr:`config` handling as needed.
    """

    def __init__(self, config: ProviderConfig | None = None) -> None:
        self.config: ProviderConfig = (
            config or ProviderConfig(name=self.__class__.__name__)
        )

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return ``True`` when the provider is reachable and authenticated."""
        raise NotImplementedError

    @property
    def provider_name(self) -> str:
        return self.config.name

    @property
    def model_name(self) -> Optional[str]:
        return self.config.model
