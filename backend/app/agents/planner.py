"""
Planner Agent.

The Planner Agent is the first step in the workflow.  It receives the raw
user request and produces a high-level plan describing what kind of visual
will be generated and how the workflow should proceed.

Future implementation: will use LLM reasoning to decompose the user's
prompt into a structured plan.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentBase, AgentContext, AgentResult
from app.core.exceptions import PlanningError
from app.models.schemas import Complexity, VisualRequest, VisualType


class PlannerAgent(AgentBase):
    """First-step agent that analyses the user request and creates a plan."""

    def __init__(self, text_generator=None) -> None:
        super().__init__(name="PlannerAgent", text_generator=text_generator)

    async def run(self, context: AgentContext) -> AgentResult:
        """Analyse the request and produce a plan.

        The plan currently is a lightweight dict containing:
          - ``visual_type``: confirmed target type
          - ``complexity``: confirmed complexity level
          - ``summary``: a brief description of the planned visual
          - ``routing``: which agent should handle the request

        In Phase 2+ this will delegate to an LLM for richer planning.
        """
        request: VisualRequest | None = context.request
        if request is None:
            return AgentResult.fail("No VisualRequest found in context.")

        try:
            plan: dict[str, Any] = await self._build_plan(request)
        except Exception as exc:
            raise PlanningError(f"Planner failed: {exc}") from exc

        return AgentResult.ok(
            data=plan,
            plan=plan,
        )

    async def _build_plan(self, request: VisualRequest) -> dict[str, Any]:
        """Build the initial plan.

        For Phase 1 this resolves ``visual_type`` and ``complexity`` and
        performs basic validation.  Full LLM-based planning comes later.
        """
        visual_type: VisualType = request.visual_type
        complexity: Complexity = request.complexity

        # Resolve AUTO to a default type (will be handled by the Router).
        if visual_type == VisualType.AUTO:
            visual_type = VisualType.INFOGRAPHIC

        return {
            "visual_type": visual_type.value,
            "complexity": complexity.value,
            "summary": (
                f"Plan for {visual_type.value} visual with "
                f"{complexity.value} complexity based on prompt: "
                f"{request.prompt[:100]}..."
            ),
            "routing": "infographic",  # default; Router overrides
        }
