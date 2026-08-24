"""
Revision Agent.

When the Critic Agent determines that a generated image does not meet
quality standards (``passed = False``), the Revision Agent refines the
prompt, design plan, or parameters and triggers a regeneration.

Future implementation: will use LLM reasoning to analyze critic feedback
and produce improved prompts / parameters.
"""

from __future__ import annotations

from app.agents.base import AgentBase, AgentContext, AgentResult
from app.core.exceptions import RevisionError


class RevisionAgent(AgentBase):
    """Improves generation quality based on critic feedback."""

    def __init__(self, text_generator=None) -> None:
        super().__init__(name="RevisionAgent", text_generator=text_generator)

    async def run(self, context: AgentContext) -> AgentResult:
        """Analyse critic feedback and produce a revised plan / prompt.

        Phase 1: returns a placeholder result indicating revision is not
        yet implemented.
        """
        if context.critic_report is None:
            return AgentResult.fail("No critic report in context — cannot revise.")

        try:
            revision = await self._revise(context)
        except Exception as exc:
            raise RevisionError(f"Revision failed: {exc}") from exc

        return AgentResult.ok(
            data=revision,
            image_prompt=revision,
            iteration=context.iteration + 1,
            status="revising",
        )

    async def _revise(self, context: AgentContext):
        """Produce a revised image prompt based on critic feedback.

        Phase 1: returns the original image prompt unchanged, with a note
        that revision logic is not yet implemented.
        """
        original_prompt = context.image_prompt
        if original_prompt is None:
            from app.models.schemas import ImagePrompt
            original_prompt = ImagePrompt(prompt=context.request.prompt if context.request else "")

        # Future: incorporate critic_report.suggestions into an improved prompt.
        original_prompt.metadata["revision_note"] = (
            "Revision agent not yet implemented in Phase 1. "
            "Using original prompt unchanged."
        )

        return original_prompt
