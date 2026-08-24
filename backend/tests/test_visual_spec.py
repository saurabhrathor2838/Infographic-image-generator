"""
Tests for the :class:`~app.models.visual_spec.VisualSpecification` Pydantic schema.

Covers:
  - A valid sample (Water Cycle) validates cleanly.
  - A minimal spec (title only) is accepted with defaults.
  - Required-title validation (empty / whitespace).
  - Layout dimension constraints.
  - Per-shape geometry requirements.
  - Colour validation across all colour-bearing fields.
  - Connection integrity (must reference existing node ids).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.visual_spec import (
    VisualSpecification,
    Layout,
    Shape,
    ShapeType,
    TextElement,
    Node,
    Section,
    Connection,
)
from app.samples import water_cycle_spec


# ── Happy paths ─────────────────────────────────────────────────────────────

def test_water_cycle_sample_validates() -> None:
    """The bundled Water Cycle sample must validate without error."""
    spec = VisualSpecification.model_validate(water_cycle_spec())
    assert spec.title == "The Water Cycle"
    assert len(spec.nodes) == 6
    assert len(spec.connections) == 6


@pytest.mark.parametrize(
    "title", ["Minimal", "A slightly longer title"]
)
def test_minimal_spec_accepted(title: str) -> None:
    """Only a title is required; everything else defaults."""
    spec = VisualSpecification(title=title)
    assert spec.title == title
    # Layout defaults to a sensible canvas.
    assert spec.layout.width == 900.0
    assert spec.layout.height == 650.0
    assert spec.sections == []
    assert spec.nodes == []


# ── Title validation ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("title", ["", "   ", "\t\n"])
def test_empty_or_whitespace_title_rejected(title: str) -> None:
    with pytest.raises(ValidationError):
        VisualSpecification(title=title)


def test_title_too_long_rejected() -> None:
    with pytest.raises(ValidationError):
        VisualSpecification(title="x" * 201)


# ── Layout constraints ───────────────────────────────────────────────────────

@pytest.mark.parametrize("width,height", [(0, 600), (-10, 600), (800, 0)])
def test_non_positive_dimensions_rejected(width, height) -> None:
    with pytest.raises(ValidationError):
        Layout(width=width, height=height)


def test_invalid_background_color_rejected() -> None:
    with pytest.raises(ValidationError):
        Layout(background="not-a-color")


# ── Shape geometry ───────────────────────────────────────────────────────────

def test_circle_requires_radius() -> None:
    with pytest.raises(ValidationError):
        Shape(type=ShapeType.CIRCLE)  # no 'r'


def test_ellipse_requires_radii() -> None:
    with pytest.raises(ValidationError):
        Shape(type=ShapeType.ELLIPSE, cx=0, cy=0)  # no rx/ry


def test_rect_requires_width_and_height() -> None:
    with pytest.raises(ValidationError):
        Shape(type=ShapeType.RECT, x=0, y=0)  # no width/height


def test_line_requires_all_endpoints() -> None:
    with pytest.raises(ValidationError):
        Shape(type=ShapeType.LINE, x1=0, y1=0, x2=10)  # missing y2


def test_polygon_requires_points() -> None:
    with pytest.raises(ValidationError):
        Shape(type=ShapeType.POLYGON)


def test_shape_invalid_color_rejected() -> None:
    with pytest.raises(ValidationError):
        Shape(type=ShapeType.RECT, width=10, height=10, fill="rgb(missing-paren")


# ── Text / node / section colours ───────────────────────────────────────────

def test_text_element_invalid_fill_rejected() -> None:
    with pytest.raises(ValidationError):
        TextElement(text="hi", x=0, y=0, fill="not-a-color")


def test_node_invalid_colors_rejected() -> None:
    with pytest.raises(ValidationError):
        Node(id="a", label="A", x=0, y=0, fill="bad")


def test_section_invalid_text_color_rejected() -> None:
    with pytest.raises(ValidationError):
        Section(title="S", text_color="#zzzzzz")


# ── Connection integrity ────────────────────────────────────────────────────

def test_connection_references_missing_node_rejected() -> None:
    with pytest.raises(ValidationError):
        VisualSpecification(
            title="T",
            nodes=[Node(id="a", label="A", x=0, y=0)],
            connections=[Connection(source="a", target="b")],
        )


def test_connection_without_nodes_rejected() -> None:
    with pytest.raises(ValidationError):
        VisualSpecification(
            title="T",
            connections=[Connection(source="a", target="b")],
        )


def test_valid_connections_accepted() -> None:
    spec = VisualSpecification(
        title="T",
        nodes=[
            Node(id="a", label="A", x=0, y=0, width=100, height=50),
            Node(id="b", label="B", x=120, y=0, width=100, height=50),
        ],
        connections=[Connection(source="a", target="b")],
    )
    assert len(spec.connections) == 1
