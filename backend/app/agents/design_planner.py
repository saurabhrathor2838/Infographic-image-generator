"""
Design Planner.

Takes a :class:`VisualRequest` (and optionally a high-level plan) and
produces a detailed :class:`DesignPlan` containing layout, color palette,
typography, key elements, and structural notes.

Future implementation: will use LLM reasoning to create rich design plans
tailored to the visual type (infographic vs complexity).
"""

from __future__ import annotations

from app.agents.base import AgentBase, AgentContext, AgentResult
from app.core.exceptions import DesignError
from app.models.schemas import DesignPlan, VisualRequest


class DesignPlanner(AgentBase):
    """Produces a structured :class:`DesignPlan` from the user request."""

    def __init__(self, text_generator=None) -> None:
        super().__init__(name="DesignPlanner", text_generator=text_generator)

    async def run(self, context: AgentContext) -> AgentResult:
        """Generate a :class:`DesignPlan` describing the visual's design.

        Phase 1: returns a basic plan with placeholder defaults.
        """
        request: VisualRequest | None = context.request
        if request is None:
            return AgentResult.fail("No VisualRequest found in context.")

        try:
            design_plan: DesignPlan = await self._create_design_plan(request)
        except Exception as exc:
            raise DesignError(f"Design planning failed: {exc}") from exc

        return AgentResult.ok(
            data=design_plan,
            design_plan=design_plan,
            status="planning",
        )

    async def _create_design_plan(self, request: VisualRequest) -> DesignPlan:
        """Create a design plan.

        Phase 1: heuristic defaults based on complexity level.
        Future: LLM-generated design plans with specific layout and style guidance.
        """
        complexity = request.complexity

        if complexity.value == "low":
            color_palette = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D"]
            layout = "single-column, clean and minimal"
        elif complexity.value == "high":
            color_palette = ["#1B1B47", "#3B2E5A", "#7D5BA6", "#B589CF"]
            layout = "multi-section, data-dense, modular grid"
        else:  # medium
            color_palette = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#FFFFFF"]
            layout = "two-column, balanced visual hierarchy"

        return DesignPlan(
            layout=layout,
            color_palette=color_palette,
            typography={
                "heading": "Bold sans-serif",
                "body": "Readable sans-serif",
                "accent": "Monospace for data",
            },
            key_elements=[
                "Title / headline",
                "Visual data representation",
                "Supporting text blocks",
                "Brand / source attribution",
            ],
            structure_notes=(
                f"Design for a {complexity.value}-complexity "
                f"{request.visual_type.value.replace('_', ' ')} visual. "
                f"Prompt: {request.prompt[:200]}."
            ),
            mood="professional, informative, visually engaging",
        )
