"""
Generation endpoint — ``POST /api/generate``

Accepts a visual-generation request, runs it through the
:class:`~app.services.orchestrator.GenerationOrchestrator`, and returns a
structured response.

Phase 2 note
─────────────
Image generation is **mocked** — no paid AI APIs are called.  The orchestrator
runs the Planner → Router → Specialist agent workflow and returns a plan,
routing decision, and a placeholder result.  Real image generation is
deferred to Phase 4+.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.core.exceptions import AppError, OrchestrationError
from app.models.schemas import GenerationStatus, VisualRequest
from app.schemas.request import GenerationRequest
from app.schemas.response import GenerationResponse
from app.services.orchestrator import GenerationOrchestrator

router: APIRouter = APIRouter()


@router.post(
    "/generate",
    response_model=GenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a visual",
    description=(
        "Submit a request to generate an infographic or complexity image. "
        "The request is processed through the agentic AI workflow "
        "(Planner → Router → Specialist Agent)."
    ),
    response_description="Generation request accepted and processed.",
)
async def generate_visual(
    request: GenerationRequest,
) -> GenerationResponse:
    """Process a visual-generation request.

    Parameters
    ----------
    request:
        Validated :class:`GenerationRequest` containing the user's prompt,
        visual type, and complexity level.

    Returns
    -------
    GenerationResponse
        Response with ``request_id``, ``status``, ``visual_type``, and
        ``message`` fields, plus an optional ``result`` dict containing
        the generation plan and routing information.
    """
    # Convert the API-level request to a domain model.
    visual_request: VisualRequest = VisualRequest(
        prompt=request.prompt,
        visual_type=request.visual_type,
        complexity=request.complexity,
    )

    # Create the orchestrator (no providers — fully mocked for Phase 2).
    orchestrator: GenerationOrchestrator = GenerationOrchestrator()

    try:
        # Run the full agentic workflow.
        result = await orchestrator.generate(visual_request)
    except AppError:
        # AppError subclasses (OrchestrationError, etc.) are handled by the
        # global exception handler in main.py → returns 500 JSONResponse.
        raise
    except Exception as exc:
        # Catch-all for unexpected errors.
        raise OrchestrationError(
            f"Unexpected error during generation: {exc}"
        ) from exc

    # ── Build the API response ────────────────────────────────────────────

    routing: str = "unknown"
    if result.plan and isinstance(result.plan, dict):
        routing = result.plan.get("routing", "unknown")

    visual_type_value: str = visual_request.visual_type.value

    # Construct a human-readable message.
    if result.status == GenerationStatus.COMPLETE:
        message: str = (
            f"Visual plan created and routed to the "
            f"'{routing}' agent. "
            f"Image generation is mocked for Phase 2."
        )
    elif result.status == GenerationStatus.FAILED:
        message = f"Generation failed: {result.error or 'Unknown error.'}"
    else:
        message = f"Generation is {result.status.value}."

    result_data: dict = {
        "visual_type": visual_type_value,
        "complexity": visual_request.complexity.value,
        "routing": routing,
        "plan": result.plan,
        "iterations": result.iterations,
        "final_image": None,
        "mock": True,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "updated_at": result.updated_at.isoformat() if result.updated_at else None,
    }

    return GenerationResponse(
        request_id=result.request_id,
        status=result.status.value,
        visual_type=visual_type_value,
        message=message,
        result=result_data,
    )
