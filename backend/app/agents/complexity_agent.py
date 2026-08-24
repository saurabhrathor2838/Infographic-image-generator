"""
Complexity Agent.

Handles the complexity-image sub-workflow:
  Design Planner → Image Prompt Generator → Image Generator → Critic → (Revision if needed)

Complexity images are technical, data-rich, or abstract visuals that may
include charts, diagrams, or complex compositions.

Future implementation: will coordinate design planning and complexity-
specific prompt generation.
"""

from __future__ import annotations

from app.agents.base import AgentBase, AgentContext, AgentResult


class ComplexityAgent(AgentBase):
    """Specialist agent for generating complexity (technical) visuals."""

    def __init__(self, text_generator=None, image_generator=None) -> None:
        super().__init__(name="ComplexityAgent", text_generator=text_generator)
        self._image_generator = image_generator

    @property
    def image_generator(self):
        return self._image_generator

    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the complexity-image sub-workflow.

        Phase 1: skeleton — records the routed target and returns a
        structured placeholder indicating that generation has not yet
        been implemented.
        """
        if context.request is None:
            return AgentResult.fail("No request in context.")

        return AgentResult.ok(
            data={
                "agent": self.name,
                "target": "complexity",
                "message": "Complexity workflow not yet implemented.",
                "status": "pending",
            },
            status="planning",
        )
