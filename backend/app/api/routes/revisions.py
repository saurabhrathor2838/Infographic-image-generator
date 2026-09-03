"""
Revision and template API endpoints.

Endpoints
---------
- ``GET  /api/templates``      — return all available templates with display names.
- ``POST /api/revisions``     — generate a spec from a prompt, run the
  :class:`~app.agents.revision_engine.RevisionEngine` (which wraps the
  :class:`~app.critics.quality_critic.VisualQualityCritic`), and return the
  final SVG, PNG, quality report and revision count.

All image generation is 100% Python (SVGRenderer + PNGRenderer) — no AI
image-generation APIs are used.
"""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.agents.revision_engine import RevisionEngine, RevisionResult
from app.models.schemas import Complexity, VisualType
from app.models.quality_report import QualityReport
from app.templates.engine import TemplateEngine

router = APIRouter()

# ── Display-name mapping (internal name → human-readable) ────────────────────

_TEMPLATE_DISPLAY: Dict[str, str] = {
    "process_flow": "Process Flow",
    "timeline": "Timeline",
    "comparison": "Comparison",
    "cycle": "Cycle",
    "hierarchy": "Hierarchy",
    "statistics": "Statistics",
    "technical_system": "Technical System",
    "step_by_step": "Step by Step",
}

_VISUAL_TYPE_DISPLAY: Dict[str, str] = {
    "auto": "Auto (let the AI decide)",
    "infographic": "Infographic",
    "complexity_image": "Complexity Image",
}


# ── Request / response schemas ───────────────────────────────────────────────


class RevisionRequest(BaseModel):
    """Payload for ``POST /api/revisions``."""

    prompt: str = Field(
        ..., min_length=1, max_length=5000,
        description="Natural-language description of the desired visual.",
    )
    visual_type: str = Field(
        default="auto",
        description="Visual type: 'auto', 'infographic', or 'complexity_image'.",
    )
    complexity: str = Field(
        default="medium",
        description="Complexity level: 'low', 'medium', or 'high'.",
    )
    template: Optional[str] = Field(
        default=None,
        description="Specific template name (e.g. 'process_flow'). If null, auto-selected.",
    )

    @field_validator("complexity")
    @classmethod
    def _validate_complexity(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("low", "medium", "high"):
            raise ValueError("complexity must be 'low', 'medium', or 'high'")
        return v

    @field_validator("visual_type")
    @classmethod
    def _validate_visual_type(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("auto", "infographic", "complexity_image"):
            raise ValueError("visual_type must be 'auto', 'infographic', or 'complexity_image'")
        return v

    @field_validator("prompt")
    @classmethod
    def _validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Prompt must not be empty or whitespace only.")
        return v


class TemplateInfo(BaseModel):
    """Metadata about a single template."""

    name: str
    display_name: str
    description: str


class QualityReportData(BaseModel):
    """Serialized :class:`QualityReport`."""

    passed: bool
    score: float
    issues: List[str]
    warnings: List[str]
    suggestions: List[str]


class RevisionResponse(BaseModel):
    """Response returned by ``POST /api/revisions``."""

    success: bool = Field(default=True)
    svg: str = Field(..., description="Rendered SVG document string.")
    png_base64: Optional[str] = Field(
        default=None,
        description="PNG image as a base64-encoded string, or null if not rendered.",
    )
    quality_report: QualityReportData = Field(
        ..., description="Final quality report from the critic.",
    )
    revisions: int = Field(..., ge=0, description="Number of revision attempts (0 = passed first try).")
    passed: bool = Field(..., description="True if the final report has zero issues.")
    template: str = Field(..., description="Template name used to generate the spec.")
    visual_type: str
    complexity: str
    prompt: str


class TemplatesResponse(BaseModel):
    """Response returned by ``GET /api/templates``."""

    templates: List[TemplateInfo]
    visual_types: List[Dict[str, str]]
    complexities: List[Dict[str, str]]


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get(
    "/templates",
    response_model=TemplatesResponse,
    status_code=status.HTTP_200_OK,
    summary="List available templates and options",
    description=(
        "Returns all available infographic templates (with display names and "
        "descriptions), visual type options, and complexity levels that the "
        "frontend can use to populate selector controls."
    ),
)
async def list_templates() -> TemplatesResponse:
    """Return available templates, visual types, and complexity levels."""
    template_infos: List[TemplateInfo] = []
    for name in TemplateEngine.available_templates():
        template_infos.append(TemplateInfo(
            name=name,
            display_name=_TEMPLATE_DISPLAY.get(name, name.replace("_", " ").title()),
            description=_template_description(name),
        ))

    visual_types = [
        {"value": k, "label": v} for k, v in _VISUAL_TYPE_DISPLAY.items()
    ]
    complexities = [
        {"value": "low", "label": "Low"},
        {"value": "medium", "label": "Medium"},
        {"value": "high", "label": "High"},
    ]

    return TemplatesResponse(
        templates=template_infos,
        visual_types=visual_types,
        complexities=complexities,
    )


def _template_description(name: str) -> str:
    """Return a human-friendly description for a template."""
    descriptions: Dict[str, str] = {
        "process_flow": "Linear steps connected by arrows — ideal for workflows and processes.",
        "timeline": "Events on a horizontal time axis — perfect for historical or chronological data.",
        "comparison": "Side-by-side comparison of two columns — great for comparing two options.",
        "cycle": "Nodes arranged in a circle with a cyclic flow — for cyclical or feedback-loop diagrams.",
        "hierarchy": "Tree structure with parent-to-child connections — for org charts and hierarchies.",
        "statistics": "Bar chart with values and trend lines — for data visualisation and metrics.",
        "technical_system": "Component diagram with data-flow arrows — for architecture and system design.",
        "step_by_step": "Numbered steps in a vertical flow — for tutorials and how-to guides.",
    }
    return descriptions.get(name, "")


@router.post(
    "/revisions",
    response_model=RevisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a visual with automatic quality revision",
    description=(
        "Generates a visual specification from the user's prompt using the "
        "TemplateEngine, runs it through the RevisionEngine (which critiques "
        "the spec and automatically fixes issues like out-of-bounds elements, "
        "broken connections, overlaps, and complexity mismatches), then renders "
        "the final spec to SVG and PNG. Returns the rendered images, a quality "
        "report, and the number of revision attempts. Maximum 3 revision "
        "attempts. All image generation is pure Python — no AI image APIs."
    ),
    responses={
        400: {"description": "Invalid request (empty prompt, unknown template, etc.)."},
    },
)
async def generate_with_revision(request: RevisionRequest) -> RevisionResponse:
    """Generate a visual specification, run the revision loop, and return rendered images."""
    # Validate template if provided.
    template: Optional[str] = None
    if request.template:
        if request.template not in TemplateEngine.available_templates():
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unknown template '{request.template}'. "
                    f"Available: {', '.join(TemplateEngine.available_templates())}"
                ),
            )
        template = request.template

    # Generate the initial spec from the prompt.
    try:
        spec = TemplateEngine.generate(
            prompt=request.prompt,
            template=template,
            complexity=request.complexity,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Spec generation failed: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate specification: {exc}",
        ) from exc

    # Run the revision engine.
    try:
        engine = RevisionEngine()
        result: RevisionResult = engine.revise(
            spec,
            prompt=request.prompt,
            complexity=request.complexity,
            render_png=True,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Revision engine failed: {exc}",
        ) from exc

    # Encode PNG as base64 for JSON transport.
    png_b64: Optional[str] = None
    if result.png is not None:
        png_b64 = base64.b64encode(result.png).decode("ascii")

    # Serialize the quality report.
    quality_data = QualityReportData(**result.report.model_dump())

    return RevisionResponse(
        success=True,
        svg=result.svg,
        png_base64=png_b64,
        quality_report=quality_data,
        revisions=result.revisions,
        passed=result.passed,
        template=template or TemplateEngine.select_template(request.prompt),
        visual_type=request.visual_type,
        complexity=request.complexity,
        prompt=request.prompt,
    )


__all__ = [
    "router",
    "RevisionRequest",
    "RevisionResponse",
    "TemplatesResponse",
    "TemplateInfo",
    "QualityReportData",
]
