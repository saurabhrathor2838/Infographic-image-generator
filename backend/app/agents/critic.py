"""
Critic Agent.

Evaluates a generated image against the original request and design plan.
Returns a :class:`CriticReport` containing a pass/fail decision, a score,
and actionable feedback.

Future implementation: will use vision-language models (e.g. GPT-4V, Claude 3
Sonnet Vision) to evaluate whether the generated image meets the criteria.
"""

from __future__ import annotations

from app.agents.base import AgentBase, AgentContext, AgentResult
from app.core.exceptions import CritiqueError
from app.models.schemas import CriticReport


class CriticAgent(AgentBase):
    """Evaluates generated images and decides whether to accept or revise."""

    PASS_THRESHOLD: float = 0.8

    def __init__(self, text_generator=None, vision_model=None) -> None:
        super().__init__(name="CriticAgent", text_generator=text_generator)
        self._vision_model = vision_model

    @property
    def vision_model(self):
        return self._vision_model

    async def run(self, context: AgentContext) -> AgentResult:
        """Evaluate the generated image.

        Phase 1: returns a placeholder report (not yet implemented).
        """
        if context.generated_image is None:
            return AgentResult.fail("No generated image in context to critique.")

        try:
            report: CriticReport = await self._evaluate(context)
        except Exception as exc:
            raise CritiqueError(f"Critique failed: {exc}") from exc

        return AgentResult.ok(
            data=report,
            critic_report=report,
            status="complete" if report.passed else "revising",
        )

    async def _evaluate(self, context: AgentContext) -> CriticReport:
        """Evaluate the image against design criteria.

        Phase 1: returns a not-passed report indicating the critic is not
        yet implemented.  No fake AI response.
        """
        return CriticReport(
            passed=False,
            score=0.0,
            feedback="Critic agent is not yet implemented in Phase 1.",
            suggestions=["Implement vision-model-based evaluation in a future phase."],
            metadata={"implemented": False},
        )
