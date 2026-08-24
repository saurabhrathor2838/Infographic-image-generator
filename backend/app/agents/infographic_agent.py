"""
Infographic Agent.

Handles the infographic-generation sub-workflow:
  Design Planner → Image Prompt Generator → Image Generator → Critic → (Revision if needed)

Future implementation: will coordinate design planning and infographic-
specific prompt generation.
"""

from __future__ import annotations

from app.agents.base import AgentBase, AgentContext, AgentResult
from app.core.exceptions import AgentError


class InfographicAgent(AgentBase):
    """Specialist agent for generating infographic visuals."""

    def __init__(self, text_generator=None, image_generator=None) -> None:
        super().__init__(name="InfographicAgent", text_generator=text_generator)
        self._image_generator = image_generator

    @property
    def image_generator(self):
        return self._image_generator

    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the infographic sub-workflow.

        Phase 1: skeleton — records the routed target and returns a
        structured placeholder indicating that generation has not yet
        been implemented.
        """
        if context.request is None:
            return AgentResult.fail("No request in context.")

        # Delegate to DesignPlanner → PromptGenerator → ImageGenerator → Critic
        # (to be implemented in later phases).
        return AgentResult.ok(
            data={
                "agent": self.name,
                "target": "infographic",
                "message": "Infographic workflow not yet implemented.",
                "status": "pending",
            },
            status="planning",  # will be updated as workflow progresses
        )
