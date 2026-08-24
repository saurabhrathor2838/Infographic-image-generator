"""
Visual specification domain models.

A :class:`VisualSpecification` is a declarative, JSON-serialisable description of
an infographic / diagram: a title, an overall canvas layout, and a collection
of visual primitives (text boxes, shapes, arrows, nodes and connections) plus
named sections that group related content.

These models are intentionally framework-agnostic so they can be validated,
rendered (see :mod:`app.renderers.svg_renderer`) and served by the API without
any AI or paid provider involvement.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Colour helper ────────────────────────────────────────────────────────────

# Accepts hex (#rgb, #rrggbb, #rrggbbaa, 3/4/6/8 digits) or rgb()/rgba() notation.
_COLOR_RE = re.compile(
    r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$"
    r"|^(rgb|rgba)\([^)]*\)$",
    re.IGNORECASE,
)


def validate_color(value: str) -> str:
    """Validate that *value* is a supported SVG colour string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("color must be a non-empty string")
    if not _COLOR_RE.match(value):
        raise ValueError(f"invalid color value: {value!r}")
    return value


# ── Enumerations ─────────────────────────────────────────────────────────────

class TextAlign(str, Enum):
    """Horizontal text alignment."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class ShapeType(str, Enum):
    """Supported SVG primitive shapes."""

    RECT = "rect"
    ROUNDED_RECT = "rounded_rect"
    CIRCLE = "circle"
    ELLIPSE = "ellipse"
    LINE = "line"
    POLYLINE = "polyline"
    POLYGON = "polygon"


# ── Layout ───────────────────────────────────────────────────────────────────

class Layout(BaseModel):
    """Canvas dimensions and background for the visual."""

    width: float = Field(default=800.0, description="Canvas width in pixels.", gt=0)
    height: float = Field(default=600.0, description="Canvas height in pixels.", gt=0)
    background: str = Field(default="#ffffff", description="Canvas background color.")
    padding: float = Field(default=40.0, description="Inner padding in pixels.", ge=0)

    @field_validator("background")
    @classmethod
    def _validate_background(cls, v: str) -> str:
        return validate_color(v)


# ── Text ─────────────────────────────────────────────────────────────────────

class TextElement(BaseModel):
    """A single block of text placed at a coordinate."""

    text: str = Field(..., min_length=1, max_length=2000)
    x: float
    y: float
    font_size: float = Field(default=16.0, gt=0)
    font_family: str = Field(default="Arial, Helvetica, sans-serif")
    fill: str = Field(default="#1e293b")
    weight: str = Field(default="normal")
    align: TextAlign = TextAlign.CENTER

    @field_validator("fill")
    @classmethod
    def _validate_fill(cls, v: str) -> str:
        return validate_color(v)


# ── Shapes ───────────────────────────────────────────────────────────────────

class Shape(BaseModel):
    """A generic SVG shape primitive."""

    type: ShapeType
    # rect / rounded_rect
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    rx: Optional[float] = None  # corner radius for rounded rect / ellipse x-radius
    ry: Optional[float] = None  # ellipse y-radius
    # circle / ellipse
    cx: Optional[float] = None
    cy: Optional[float] = None
    r: Optional[float] = None  # circle radius
    # line
    x1: Optional[float] = None
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None
    # polyline / polygon
    points: Optional[str] = None
    # styling
    fill: str = Field(default="#ffffff")
    stroke: str = Field(default="#1e293b")
    stroke_width: float = Field(default=1.0, ge=0)
    opacity: float = Field(default=1.0, ge=0, le=1)

    @field_validator("fill", "stroke")
    @classmethod
    def _validate_colors(cls, v: str) -> str:
        return validate_color(v)

    @model_validator(mode="after")
    def _validate_geometry(self) -> "Shape":
        t = self.type
        if t in (ShapeType.RECT, ShapeType.ROUNDED_RECT):
            if self.width is None or self.height is None:
                raise ValueError(
                    f"{t.value} requires 'width' and 'height'"
                )
        elif t == ShapeType.CIRCLE:
            if self.r is None:
                raise ValueError("circle requires 'r'")
        elif t == ShapeType.ELLIPSE:
            if self.rx is None or self.ry is None:
                raise ValueError("ellipse requires 'rx' and 'ry'")
        elif t == ShapeType.LINE:
            if None in (self.x1, self.y1, self.x2, self.y2):
                raise ValueError("line requires 'x1', 'y1', 'x2' and 'y2'")
        elif t in (ShapeType.POLYLINE, ShapeType.POLYGON):
            if not self.points:
                raise ValueError(f"{t.value} requires non-empty 'points'")
        return self


class Arrow(BaseModel):
    """A directed line segment with an optional arrowhead."""

    x1: float
    y1: float
    x2: float
    y2: float
    stroke: str = Field(default="#64748b")
    stroke_width: float = Field(default=2.0, ge=0)
    marker: bool = Field(default=True, description="Render an arrowhead at the tip.")

    @field_validator("stroke")
    @classmethod
    def _validate_stroke(cls, v: str) -> str:
        return validate_color(v)


# ── Nodes & connections ──────────────────────────────────────────────────────

class Node(BaseModel):
    """A labelled graph node rendered as a box or circle."""

    id: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=200)
    x: float
    y: float
    width: float = Field(default=120.0, gt=0)
    height: float = Field(default=60.0, gt=0)
    fill: str = Field(default="#f0f2f5")
    stroke: str = Field(default="#2563eb")
    stroke_width: float = Field(default=2.0, ge=0)
    font_size: float = Field(default=14.0, gt=0)
    shape: str = Field(default="rounded_rect")

    @field_validator("fill", "stroke")
    @classmethod
    def _validate_colors(cls, v: str) -> str:
        return validate_color(v)


class Connection(BaseModel):
    """A directed edge between two nodes, referenced by ``id``."""

    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    stroke: str = Field(default="#64748b")
    stroke_width: float = Field(default=2.0, ge=0)

    @field_validator("stroke")
    @classmethod
    def _validate_stroke(cls, v: str) -> str:
        return validate_color(v)


# ── Sections ─────────────────────────────────────────────────────────────────

class Section(BaseModel):
    """A titled, optionally described container drawn on the canvas."""

    title: str = Field(..., min_length=1, max_length=200)
    x: float = 0.0
    y: float = 0.0
    width: float = Field(default=200.0, gt=0)
    height: float = Field(default=120.0, gt=0)
    fill: str = Field(default="#f8fafc")
    stroke: str = Field(default="#e2e8f0")
    stroke_width: float = Field(default=1.0, ge=0)
    text_color: str = Field(default="#1e293b")
    description: Optional[str] = None

    @field_validator("fill", "stroke", "text_color")
    @classmethod
    def _validate_colors(cls, v: str) -> str:
        return validate_color(v)


# ── Root specification ───────────────────────────────────────────────────────

class VisualSpecification(BaseModel):
    """A complete, renderable description of a visual.

    The spec is the single input consumed by
    :class:`app.renderers.svg_renderer.SVGRenderer`.  It is fully JSON
    serialisable and validated by Pydantic before rendering.
    """

    title: str = Field(..., min_length=1, max_length=200)
    layout: Layout = Field(default_factory=lambda: Layout(width=900.0, height=650.0))
    title_font_size: float = Field(default=36.0, gt=0)
    title_fill: str = Field(default="#0f172a")
    sections: List[Section] = Field(default_factory=list)
    text: List[TextElement] = Field(default_factory=list)
    shapes: List[Shape] = Field(default_factory=list)
    arrows: List[Arrow] = Field(default_factory=list)
    nodes: List[Node] = Field(default_factory=list)
    connections: List[Connection] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty or whitespace only")
        return v

    @field_validator("title_fill")
    @classmethod
    def _validate_title_fill(cls, v: str) -> str:
        return validate_color(v)

    @model_validator(mode="after")
    def _validate_connections(self) -> "VisualSpecification":
        """Every connection must reference an existing node id."""
        if self.connections:
            if not self.nodes:
                raise ValueError(
                    "connections require at least one node to reference"
                )
            ids = {n.id for n in self.nodes}
            for conn in self.connections:
                if conn.source not in ids:
                    raise ValueError(
                        f"connection source {conn.source!r} does not match any node id"
                    )
                if conn.target not in ids:
                    raise ValueError(
                        f"connection target {conn.target!r} does not match any node id"
                    )
        return self
