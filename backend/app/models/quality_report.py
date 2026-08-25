"""
Quality report model for the visual quality critic.

A :class:`QualityReport` is a structured summary of automated checks performed
on a :class:`~app.models.visual_spec.VisualSpecification` and / or the SVG
document it produces.  It collects *issues* (critical failures), *warnings*
(non-critical concerns) and *suggestions* (improvement recommendations) into
a single object with an overall ``score`` and ``passed`` flag.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class QualityReport(BaseModel):
    """Structured result of quality checks on a visual specification."""

    passed: bool = Field(
        ...,
        description="True when the spec has zero critical issues.",
    )
    score: float = Field(
        default=100.0,
        description="Overall quality score in the range 0–100.",
        ge=0.0,
        le=100.0,
    )
    issues: List[str] = Field(
        default_factory=list,
        description="Critical problems that make the visual invalid.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-critical concerns worth attention.",
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Recommendations for improving the visual.",
    )

    def add_issue(self, message: str) -> None:
        """Record a critical issue."""
        self.issues.append(message)

    def add_warning(self, message: str) -> None:
        """Record a non-critical warning."""
        self.warnings.append(message)

    def add_suggestion(self, message: str) -> None:
        """Record an improvement suggestion."""
        self.suggestions.append(message)

    def finalize(self) -> "QualityReport":
        """Recompute ``passed`` and ``score`` from collected findings."""
        self.passed = len(self.issues) == 0
        self.score = max(
            0.0,
            100.0
            - 25.0 * len(self.issues)
            - 5.0 * len(self.warnings)
            - 2.0 * len(self.suggestions),
        )
        return self


__all__ = ["QualityReport"]
