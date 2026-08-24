"""
Domain models for the AI Visual Generator.

These are plain Python data classes and enums used by agents, the orchestrator,
and providers.  They are intentionally framework-agnostic (no FastAPI / Pydantic
dependencies) so they can be reused in CLI tools, tests, and future services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


# ── Enumerations ─────────────────────────────────────────────────────────────

class VisualType(str, Enum):
    """The type of visual the user wants to generate."""

    AUTO = "auto"
    INFOGRAPHIC = "infographic"
    COMPLEXITY_IMAGE = "complexity_image"


class Complexity(str, Enum):
    """Complexity level for the generated visual."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GenerationType(str, Enum):
    """Which generation strategy the router selected."""

    INFOGRAPHIC = "infographic"
    COMPLEXITY = "complexity"


class GenerationStatus(str, Enum):
    """Lifecycle status of a generation request."""

    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    CRITIQUING = "critiquing"
    REVISING = "revising"
    COMPLETE = "complete"
    FAILED = "failed"


# ── Domain Data Classes ──────────────────────────────────────────────────────

@dataclass
class VisualRequest:
    """A request from the user for a visual."""

    prompt: str
    visual_type: VisualType = VisualType.AUTO
    complexity: Complexity = Complexity.MEDIUM
    request_id: str = ""

    def __post_init__(self) -> None:
        if not self.prompt or not self.prompt.strip():
            raise ValueError("Prompt must not be empty.")


@dataclass
class DesignPlan:
    """Structured design plan produced by the Design Planner."""

    layout: str = ""
    color_palette: list[str] = field(default_factory=list)
    typography: dict[str, str] = field(default_factory=dict)
    key_elements: list[str] = field(default_factory=list)
    structure_notes: str = ""
    mood: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImagePrompt:
    """A refined image-generation prompt produced by the Image Prompt Generator."""

    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    style: str = ""
    reference: Optional[str] = None  # optional reference to a previous image
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CriticReport:
    """Evaluation produced by the Critic Agent."""

    passed: bool
    score: float  # 0.0 – 1.0
    feedback: str = ""
    suggestions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedImage:
    """A single generated image and its provenance."""

    image_bytes: Optional[bytes] = None
    image_path: Optional[Path] = None
    prompt: str = ""
    provider: str = ""
    model: str = ""
    seed: Optional[int] = None
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Complete result of a generation workflow."""

    request_id: str
    request: VisualRequest
    status: GenerationStatus = GenerationStatus.PENDING
    plan: Optional[dict[str, Any]] = None
    final_image: Optional[GeneratedImage] = None
    iterations: int = 0
    critic_reports: list[CriticReport] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    error: Optional[str] = None
