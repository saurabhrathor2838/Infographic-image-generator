"""
Visualization + AI-planning endpoints.

Endpoints
---------
- ``POST /api/render``               — render a caller-supplied specification.
- ``POST /api/plan``                 — turn a natural-language prompt into a
  specification via the :class:`~app.agents.visual_planner.VisualPlannerAgent`
  and return the rendered SVG (LLM provider injected via ``get_text_generator``).
- ``GET  /api/samples/water-cycle``  — render the bundled sample as SVG.
- ``GET  /api/samples/water-cycle/spec`` — return the sample spec as JSON.

No paid API is invoked here; the LLM client is injected (and therefore
mockable in tests).  When no provider is configured, ``/api/plan`` responds
``503`` instead of failing hard.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from app.agents.base import AgentContext
from app.agents.visual_planner import VisualPlannerAgent
from app.core.exceptions import AppError
from app.models.schemas import VisualRequest
from app.models.visual_spec import VisualSpecification
from app.providers.factory import get_text_generator
from app.providers.text_generator import TextGenerator
from app.renderers.png_renderer import PNGRenderer
from app.renderers.svg_renderer import SVGRenderer
from app.samples import water_cycle, water_cycle_spec
from app.schemas.request import GenerationRequest

router: APIRouter = APIRouter()


# ── Helpers ─────────────────────────────────────────────────────────────────

def _render(spec: VisualSpecification, *, format: str = "svg") -> Response:
    """Render *spec* to an SVG or PNG ``Response``.

    Parameters
    ----------
    spec:
        The validated specification to render.
    format:
        ``"svg"`` (default) returns ``image/svg+xml``.
        ``"png"``  returns ``image/png`` rendered via Pillow.
    """
    if format == "png":
        data = PNGRenderer().render(spec)
        return Response(content=data, media_type="image/png")
    svg = SVGRenderer().render(spec)
    return Response(content=svg, media_type="image/svg+xml")


# ── Render a caller-supplied specification ───────────────────────────────────

@router.post(
    "/render",
    response_class=Response,
    status_code=200,
    summary="Render a VisualSpecification to SVG or PNG",
    description=(
        "Accepts a validated ``VisualSpecification`` JSON body, renders it to SVG "
        "(default, ``?format=svg``) or PNG (``?format=png`` via Pillow), and "
        "returns the image."
    ),
    response_description="An SVG or PNG document representing the specification.",
)
async def render_visual(
    spec: VisualSpecification,
    format: str = "svg",
) -> Response:
    """Render a caller-supplied specification to SVG or PNG."""
    if format not in ("svg", "png"):
        raise HTTPException(status_code=400, detail="format must be 'svg' or 'png'")
    return _render(spec, format=format)


# ── Plan + render from a natural-language prompt ────────────────────────────

@router.post(
    "/plan",
    response_class=Response,
    status_code=200,
    summary="Plan a visual from a prompt and render it to SVG or PNG",
    description=(
        "Accepts a natural-language prompt (plus optional visual_type and "
        "complexity), uses the AI Planner Agent to produce a validated "
        "``VisualSpecification``, renders it to SVG or PNG, and returns the "
        "image.  Pass ``?format=svg`` (default) for ``image/svg+xml`` or "
        "``?format=png`` for ``image/png`` (rendered via Pillow, no native "
        "graphics library required).  The LLM provider is injected via "
        "``get_text_generator`` and is configurable through environment "
        "variables. Returns 503 when no provider is configured, 502 when the "
        "LLM output cannot be turned into a valid specification."
    ),
    response_description="An SVG or PNG document produced from the planned specification.",
    responses={
        502: {"description": "Planning failed (invalid/empty AI output)."},
        503: {"description": "LLM provider not configured."},
    },
)
async def plan_and_render(
    request: GenerationRequest,
    text_generator: Optional[TextGenerator] = Depends(get_text_generator),
    format: str = "svg",
) -> Response:
    if format not in ("svg", "png"):
        raise HTTPException(status_code=400, detail="format must be 'svg' or 'png'")
    if text_generator is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "LLM provider not configured. Set AI_PROVIDER=openai and "
                "OPENAI_API_KEY in the environment, or AI_PROVIDER=mock for "
                "local development."
            ),
        )

    planner = VisualPlannerAgent(text_generator=text_generator)
    visual_request = VisualRequest(
        prompt=request.prompt,
        visual_type=request.visual_type,
        complexity=request.complexity,
    )
    context = AgentContext(request=visual_request)

    try:
        result = await planner.run(context)
    except AppError as exc:
        raise HTTPException(
            status_code=502, detail=f"Planning failed: {exc.message}"
        ) from exc

    if not result.success or result.data is None:
        raise HTTPException(
            status_code=502, detail=result.error or "Planning failed."
        )

    spec: VisualSpecification = result.data
    return _render(spec, format=format)


# ── Sample endpoints ──────────────────────────────────────────────────────────

@router.get(
    "/samples/water-cycle",
    response_class=Response,
    status_code=200,
    summary="Render the 'Water Cycle' sample infographic",
    description="Returns the SVG for the bundled Water Cycle sample infographic.",
)
async def sample_water_cycle() -> Response:
    return _render(water_cycle())


@router.get(
    "/samples/water-cycle/spec",
    response_model=Dict[str, Any],
    status_code=200,
    summary="Return the 'Water Cycle' specification as JSON",
    description="Returns the raw JSON of the Water Cycle sample specification.",
)
async def sample_water_cycle_spec() -> Dict[str, Any]:
    return water_cycle_spec()
