"""
Tests for :class:`~app.renderers.svg_renderer.SVGRenderer`.

Covers:
  - Minimal spec renders a well-formed SVG containing the title.
  - The Water Cycle sample renders all expected primitives and is valid XML.
  - Special characters in text are XML-escaped.
  - Arrowheads, sections, nodes, connections and shapes are all present.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from app.models.visual_spec import (
    VisualSpecification,
    Layout,
    TextElement,
    Shape,
    ShapeType,
    Node,
    Connection,
    Arrow,
)
from app.renderers.svg_renderer import SVGRenderer
from app.samples import water_cycle


# ── Helpers ──────────────────────────────────────────────────────────────────

def _render(spec: VisualSpecification) -> str:
    return SVGRenderer().render(spec)


def _localname(tag: str) -> str:
    """Strip an XML namespace prefix from an ElementTree tag."""
    return tag.split("}", 1)[-1]


def _element_counts(svg: str) -> dict:
    root = ET.fromstring(svg)
    counts: dict[str, int] = {}
    for el in root.iter():
        name = _localname(el.tag)
        counts[name] = counts.get(name, 0) + 1
    return counts


# ── Well-formedness ──────────────────────────────────────────────────────────

def test_minimal_spec_renders_svg() -> None:
    spec = VisualSpecification(title="Hello")
    svg = _render(spec)
    assert svg.startswith("<svg")
    assert svg.strip().endswith("</svg>")
    # Must be parseable XML.
    root = ET.fromstring(svg)
    assert _localname(root.tag) == "svg"


def test_svg_has_viewbox_and_dimensions() -> None:
    spec = VisualSpecification(
        title="Boxed",
        layout=Layout(width=640, height=480, background="#ffffff"),
    )
    svg = _render(spec)
    assert 'width="640"' in svg
    assert 'height="480"' in svg
    assert 'viewBox="0 0 640 480"' in svg


# ── Water Cycle sample ───────────────────────────────────────────────────────

def test_water_cycle_is_well_formed_xml() -> None:
    svg = _render(water_cycle())
    root = ET.fromstring(svg)
    assert _localname(root.tag) == "svg"


def test_water_cycle_contains_title_and_background() -> None:
    svg = _render(water_cycle())
    assert "The Water Cycle" in svg
    assert "#0f172a" in svg  # dark background


@pytest.mark.parametrize(
    "node_label",
    ["Ocean", "Evaporation", "Condensation", "Precipitation", "Runoff", "Collection"],
)
def test_water_cycle_renders_all_node_labels(node_label: str) -> None:
    svg = _render(water_cycle())
    assert node_label in svg


def test_water_cycle_renders_all_primitive_types() -> None:
    svg = _render(water_cycle())
    counts = _element_counts(svg)
    # Background + 2 sections + 6 node boxes.
    assert counts.get("rect", 0) >= 9
    # Sun.
    assert counts.get("circle", 0) >= 1
    # Sun rays (4) + raindrop arrows (3) + 6 connections = 13.
    assert counts.get("line", 0) >= 13
    # Arrowhead definition.
    assert counts.get("polygon", 0) >= 1
    assert counts.get("marker", 0) == 1
    assert counts.get("text", 0) >= 13


def test_water_cycle_arrowheads_use_marker_end() -> None:
    svg = _render(water_cycle())
    # At least one directed line carries an arrowhead.
    assert "marker-end=\"url(#arrowhead)\"" in svg


def test_water_cycle_connections_rendered() -> None:
    svg = _render(water_cycle())
    # Each connection becomes a <line ... marker-end=...>.
    assert svg.count("marker-end=\"url(#arrowhead)\"") >= 6


# ── Escaping ─────────────────────────────────────────────────────────────────

def test_special_characters_are_escaped() -> None:
    spec = VisualSpecification(
        title="A & B < C > D",
        text=[TextElement(text="<script>alert(1)</script>", x=0, y=0)],
    )
    svg = _render(spec)
    assert "&amp;" in svg
    # The raw, dangerous tags must not survive as live elements.
    assert "<script>alert(1)</script>" not in svg


# ── Direct primitive rendering ────────────────────────────────────────────────

def test_render_line_shape_without_marker() -> None:
    spec = VisualSpecification(
        title="Lines",
        shapes=[Shape(type=ShapeType.LINE, x1=0, y1=0, x2=10, y2=10)],
    )
    svg = _render(spec)
    assert "<line" in svg
    assert "marker-end" not in svg  # plain line, no arrowhead


def test_render_connection_resolves_node_ids() -> None:
    spec = VisualSpecification(
        title="Conn",
        nodes=[
            Node(id="a", label="A", x=100, y=100, width=60, height=40),
            Node(id="b", label="B", x=300, y=100, width=60, height=40),
        ],
        connections=[Connection(source="a", target="b")],
    )
    svg = _render(spec)
    # A connection renders a directed line between the two nodes.
    assert "<line" in svg
    assert svg.count("marker-end=\"url(#arrowhead)\"") == 1
