"""
Visualization endpoints.

Exposes the programmatic SVG renderer over HTTP so that a client can submit a
:class:`~app.models.visual_spec.VisualSpecification` (or request a bundled
sample) and receive a rendered SVG document back.

Endpoints
---------
- ``POST /api/render``                 — render an arbitrary specification.
- ``GET  /api/samples/water-cycle``    — render the built-in "Water Cycle" sample.
- ``GET  /api/samples/water-cycle/spec`` — return the "Water Cycle" spec as JSON.

No AI model or paid service is involved — rendering is fully deterministic
from the specification JSON.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Response

from app.models.visual_spec import VisualSpecification
from app.renderers.svg_renderer import SVGRenderer
from app.samples import water_cycle, water_cycle_spec

router: APIRouter = APIRouter()


def _render(spec: VisualSpecification) -> Response:
    """Render *spec* to SVG and wrap it in a 200 response."""
    svg = SVGRenderer().render(spec)
    return Response(content=svg, media_type="image/svg+xml")


@router.post(
    "/render",
    response_class=Response,
    status_code=200,
    summary="Render a VisualSpecification to SVG",
    description=(
        "Accepts a validated ``VisualSpecification`` JSON body, renders it to an "
        "SVG document, and returns the SVG (content-type ``image/svg+xml``). "
        "No AI or paid provider is used."
    ),
    response_description="An SVG document representing the specification.",
)
async def render_visual(spec: VisualSpecification) -> Response:
    """Render a user-supplied :class:`VisualSpecification` as SVG."""
    return _render(spec)


@router.get(
    "/samples/water-cycle",
    response_class=Response,
    status_code=200,
    summary="Render the 'Water Cycle' sample infographic",
    description="Returns the SVG for the bundled Water Cycle sample infographic.",
    response_description="An SVG document for the Water Cycle infographic.",
)
async def sample_water_cycle() -> Response:
    """Render the built-in Water Cycle sample as SVG."""
    return _render(water_cycle())


@router.get(
    "/samples/water-cycle/spec",
    response_model=Dict[str, Any],
    status_code=200,
    summary="Return the 'Water Cycle' specification as JSON",
    description="Returns the raw JSON of the Water Cycle sample specification.",
)
async def sample_water_cycle_spec() -> Dict[str, Any]:
    """Return the Water Cycle specification as a JSON-serialisable dict."""
    return water_cycle_spec()
