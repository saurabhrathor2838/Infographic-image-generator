"""
Generation Orchestrator.

Coordinates the agentic AI workflow described in the project README:

    Planner → Router → {InfographicAgent | ComplexityAgent}
                → DesignPlanner → ImagePromptGenerator
                → ImageGenerator → CriticAgent
                → {Critic PASS → Final Image | Critic FAIL → RevisionAgent → loop}

Phase 1 note
─────────────
The orchestrator in Phase 1 defines the workflow *structure* but does not
invoke any paid / image-generation APIs.  Each agent returns a structured
placeholder result.  Real provider wiring and image generation are
deferred to Phase 4+.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from app.agents.base import AgentContext, AgentResult
from app.agents.critic import CriticAgent
from app.agents.design_planner import DesignPlanner
from app.agents.image_prompt_generator import ImagePromptGenerator
from app.agents.infographic_agent import InfographicAgent
from app.agents.complexity_agent import ComplexityAgent
from app.agents.planner import PlannerAgent
from app.agents.revision_agent import RevisionAgent
from app.agents.router import RouterAgent
from app.core.exceptions import OrchestrationError
from app.models.schemas import (
    GenerationResult,
    GenerationStatus,
    VisualRequest,
)
from app.providers.image_generator import ImageGenerator
from app.providers.text_generator import TextGenerator


class GenerationOrchestrator:
    """Top-level coordinator for the visual-generation workflow."""

    def __init__(
        self,
        text_generator: TextGenerator | None = None,
        image_generator: ImageGenerator | None = None,
    ) -> None:
        self._text_generator: TextGenerator | None = text_generator
        self._image_generator: ImageGenerator | None = image_generator

        # ── Agent instances ──────────────────────────────────────────────
        self.planner: PlannerAgent = PlannerAgent(text_generator)
        self.router: RouterAgent = RouterAgent(text_generator)
        self.infographic_agent: InfographicAgent = InfographicAgent(
            text_generator, image_generator
        )
        self.complexity_agent: ComplexityAgent = ComplexityAgent(
            text_generator, image_generator
        )
        self.design_planner: DesignPlanner = DesignPlanner(text_generator)
        self.prompt_generator: ImagePromptGenerator = ImagePromptGenerator(
            text_generator
        )
        self.critic: CriticAgent = CriticAgent(text_generator)
        self.revision: RevisionAgent = RevisionAgent(text_generator)

    # ── Public API ────────────────────────────────────────────────────────

    async def generate(
        self,
        request: VisualRequest,
    ) -> GenerationResult:
        """Run the full generation workflow for a single request.

        Parameters
        ----------
        request:
            The user's :class:`VisualRequest`.

        Returns
        -------
        GenerationResult
            Structured result including status and any generated artifacts.

        Raises
        ------
        OrchestrationError
            If a non-recoverable error occurs.
        """
        request_id: str = request.request_id or str(uuid.uuid4())
        request.request_id = request_id

        context = AgentContext(
            request=request,
            request_id=request_id,
            max_iterations=getattr(
                request,
                "_max_iterations",
                3,
            ),
        )

        result = GenerationResult(
            request_id=request_id,
            request=request,
            status=GenerationStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        try:
            # ── Step 1: Plan ───────────────────────────────────────────
            context, result = await self._step_plan(context, result)

            # ── Step 2: Route ──────────────────────────────────────────
            context, result = await self._step_route(context, result)

            # ── Step 3: Specialist agent (infographic or complexity) ──
            context, result = await self._step_specialist(context, result)

        except OrchestrationError:
            raise
        except Exception as exc:
            result.status = GenerationStatus.FAILED
            result.error = str(exc)
            result.updated_at = datetime.now()
            raise OrchestrationError(
                f"Orchestration failed for request {request_id}: {exc}"
            ) from exc

        return result

    # ── Private step methods ────────────────────────────────────────────────

    async def _step_plan(
        self, context: AgentContext, result: GenerationResult
    ) -> tuple[AgentContext, GenerationResult]:
        """Execute the Planner Agent."""
        result.status = GenerationStatus.PLANNING
        result.updated_at = datetime.now()

        agent_result: AgentResult = await self.planner.run(context)
        if not agent_result.success:
            result.status = GenerationStatus.FAILED
            result.error = agent_result.error
            raise OrchestrationError(f"Planner failed: {agent_result.error}")

        context = context.update(
            plan=agent_result.context_updates.get("plan", agent_result.data),
            status=GenerationStatus.PLANNING,
        )
        result.plan = agent_result.data if isinstance(agent_result.data, dict) else None
        return context, result

    async def _step_route(
        self, context: AgentContext, result: GenerationResult
    ) -> tuple[AgentContext, GenerationResult]:
        """Execute the Router Agent."""
        agent_result: AgentResult = await self.router.run(context)
        if not agent_result.success:
            result.status = GenerationStatus.FAILED
            result.error = agent_result.error
            raise OrchestrationError(f"Router failed: {agent_result.error}")

        target: str = agent_result.data
        result.plan = {**(result.plan or {}), "routing": target}
        return context, result

    async def _step_specialist(
        self, context: AgentContext, result: GenerationResult
    ) -> tuple[AgentContext, GenerationResult]:
        """Execute the specialist agent based on router decision.

        Phase 1: the specialist agents are skeletons that return placeholder
        data.  The full sub-workflow (DesignPlanner → PromptGenerator →
        ImageGenerator → Critic → Revision) is defined but not executed
        with real providers.
        """
        routing: str = (result.plan or {}).get("routing", "infographic")

        if routing == "infographic":
            agent_result = await self.infographic_agent.run(context)
        elif routing == "complexity":
            agent_result = await self.complexity_agent.run(context)
        else:
            raise OrchestrationError(f"Unknown routing target: {routing!r}")

        if not agent_result.success:
            result.status = GenerationStatus.FAILED
            result.error = agent_result.error
            raise OrchestrationError(
                f"Specialist agent failed: {agent_result.error}"
            )

        # In Phase 1 the specialist returns placeholder metadata.
        # In Phase 2+ this will progress through design → prompt → image → critique.
        result.status = GenerationStatus.COMPLETE
        result.updated_at = datetime.now()
        return context, result

    # ── Health ─────────────────────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Check the health of the orchestrator and its providers."""
        checks: dict[str, Any] = {
            "text_generator": "configured" if self._text_generator else "not configured",
            "image_generator": "configured" if self._image_generator else "not configured",
        }
        return checks
