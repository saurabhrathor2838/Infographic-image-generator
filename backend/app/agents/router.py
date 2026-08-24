"""
Router Agent.

The Router Agent decides which specialist agent (Infographic or Complexity)
should handle a given plan.  It inspects the plan produced by the Planner and
routes the request accordingly.

Future implementation: may use LLM classification to determine the best
agent for a given request.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentBase, AgentContext, AgentResult
from app.core.exceptions import PlanningError
from app.models.schemas import GenerationType


class RouterAgent(AgentBase):
    """Routes a generation request to the appropriate specialist agent."""

    def __init__(self, text_generator=None) -> None:
        super().__init__(name="RouterAgent", text_generator=text_generator)

    async def run(self, context: AgentContext) -> AgentResult:
        """Inspect the plan and choose a downstream agent.

        Returns an :class:`AgentResult` whose ``data`` is a string
        identifying the target agent: ``"infographic"`` or
        ``"complexity"``.
        """
        plan: dict[str, Any] | None = context.plan
        if plan is None:
            return AgentResult.fail(
                "No plan found in context — run the PlannerAgent first."
            )

        try:
            target = self._route(plan)
        except Exception as exc:
            raise PlanningError(f"Router failed: {exc}") from exc

        return AgentResult.ok(
            data=target,
            target_agent=target,
            routing_decision=target,
        )

    def _route(self, plan: dict[str, Any]) -> str:
        """Determine which specialist agent to invoke.

        Phase 1 logic:
          - If ``plan['visual_type']`` is ``infographic`` → ``"infographic"``
          - If ``plan['visual_type']`` is ``complexity_image`` → ``"complexity"``
          - If ``plan['visual_type']`` is ``auto`` → default to ``"infographic"``

        Future: LLM-based classification.
        """
        visual_type: str = plan.get("visual_type", "").lower()

        if visual_type in ("infographic", "auto"):
            return GenerationType.INFOGRAPHIC.value
        elif visual_type in ("complexity_image", "complexity"):
            return GenerationType.COMPLEXITY.value
        else:
            raise PlanningError(f"Unknown or unsupported visual_type: {visual_type!r}")
