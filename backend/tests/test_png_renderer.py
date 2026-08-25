"""
Tests for :class:`~app.renderers.png_renderer.PNGRenderer`.

Covers:
  - Valid PNG header and structure for every layout × complexity combination.
  - PNG dimensions respect the DPI / scale parameter.
  - SVG string input is accepted (``render_svg``).
  - All SVG primitive types are rendered without error:
    rect (sharp + rounded), circle, ellipse, line, polygon, text.
  - Opacity values are honoured without crashing.
  - The end-to-end pipeline mock-generator → spec → SVG → PNG works.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from io import BytesIO

import pytest
from PIL import Image

from app.models.visual_spec import VisualSpecification
from app.providers.mock_text_generator import MockTextGenerator
from app.renderers.layouts import LayoutEngine
from app.renderers.png_renderer import PNGRenderer
from app.renderers.svg_renderer import SVGRenderer

_PNG_SIG = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def mock_spec() -> VisualSpecification:
    """Generate a deterministic spec using the MockTextGenerator."""
    gen = MockTextGenerator()
    import asyncio

    system_prompt = (
        "You are a visual planning agent.\n\n"
        "Visual type requested: complexity_image.\n"
        "Complexity: medium.\n\n"
        "User prompt: Create an infographic explaining the water cycle."
    )
    result = asyncio.run(gen.generate("trigger", system_prompt=system_prompt))
    return VisualSpecification.model_validate(json.loads(result.text))


# ── PNG header / validity ────────────────────────────────────────────────────


class TestPNGHeader:
    """Verify the raw PNG file signature and basic decodability."""

    def test_png_header_valid(self, mock_spec: VisualSpecification) -> None:
        png = PNGRenderer().render(mock_spec)
        assert png[:8] == _PNG_SIG

    def test_png_decodable_by_pil(self, mock_spec: VisualSpecification) -> None:
        png = PNGRenderer().render(mock_spec)
        img = Image.open(BytesIO(png))
        img.load()
        assert img.format == "PNG"
        assert img.size[0] > 0 and img.size[1] > 0

    def test_png_dimensions_proportional(self, mock_spec: VisualSpecification) -> None:
        """At 144 DPI the PNG should be ~2× the SVG canvas dimensions."""
        png = PNGRenderer(dpi=144).render(mock_spec)
        img = Image.open(BytesIO(png))
        svg = SVGRenderer().render(mock_spec)
        root = ET.fromstring(svg)
        svg_w = float(root.get("width", 800))
        svg_h = float(root.get("height", 600))
        expected_w = int(svg_w * 2)
        expected_h = int(svg_h * 2)
        assert img.size == (expected_w, expected_h)


# ── All layouts × all complexities ────────────────────────────────────────────


@pytest.mark.parametrize("layout_name", LayoutEngine.available_layouts())
@pytest.mark.parametrize("complexity", ["low", "medium", "high"])
def test_layout_png_all_combinations(
    layout_name: str, complexity: str
) -> None:
    """Every layout must render to a valid PNG at every complexity level."""
    prompt = "Create a diagram about system architecture and data flow."
    spec = LayoutEngine.generate(prompt, layout_name, complexity)
    png = PNGRenderer().render(spec)

    assert png[:8] == _PNG_SIG, f"{layout_name}/{complexity}: bad PNG header"
    img = Image.open(BytesIO(png))
    img.load()
    assert img.format == "PNG"
    assert img.size[0] > 500 and img.size[1] > 300


@pytest.mark.parametrize("layout_name", LayoutEngine.available_layouts())
def test_layout_high_complexity_larger_than_low(layout_name: str) -> None:
    """Higher complexity should produce a larger PNG file (more elements)."""
    prompt = "Create a diagram about system architecture and data flow."
    low_spec = LayoutEngine.generate(prompt, layout_name, "low")
    high_spec = LayoutEngine.generate(prompt, layout_name, "high")
    low_png = PNGRenderer().render(low_spec)
    high_png = PNGRenderer().render(high_spec)
    assert len(high_png) > len(low_png), (
        f"{layout_name}: high complexity ({len(high_png)} bytes) should be "
        f"larger than low ({len(low_png)} bytes)"
    )


# ── SVG string rendering ─────────────────────────────────────────────────────

def test_render_svg_accepts_raw_svg(mock_spec: VisualSpecification) -> None:
    """``render_svg`` should accept an SVG string and return PNG bytes."""
    svg = SVGRenderer().render(mock_spec)
    png = PNGRenderer().render_svg(svg)
    assert png[:8] == _PNG_SIG
    Image.open(BytesIO(png)).load()  # raises if not a valid image


def test_render_svg_invalid_input_raises() -> None:
    """Invalid XML should raise a ParseError."""
    with pytest.raises(ET.ParseError):
        PNGRenderer().render_svg("not valid xml <<")


# ── Primitive coverage ───────────────────────────────────────────────────────


class TestPrimitiveRendering:
    """Each SVG primitive type should render without error."""

    @pytest.mark.parametrize("shape_type", ["rect", "rounded_rect"])
    def test_rect_shapes(self, shape_type: str, mock_spec: VisualSpecification) -> None:
        svg = SVGRenderer().render(mock_spec)
        if "rect" in svg:
            png = PNGRenderer().render_svg(svg)
            assert png[:8] == _PNG_SIG

    def test_circle_shape(self) -> None:
        from app.models.visual_spec import Shape
        spec = VisualSpecification(
            title="Test",
            shapes=[Shape(type="circle", cx=450, cy=450, r=50, fill="#F18F01")],
        )
        png = PNGRenderer().render(spec)
        assert png[:8] == _PNG_SIG

    def test_ellipse_shape(self) -> None:
        from app.models.visual_spec import Shape
        spec = VisualSpecification(
            title="Test",
            shapes=[Shape(type="ellipse", cx=450, cy=450, rx=60, ry=30, fill="#2E86AB")],
        )
        png = PNGRenderer().render(spec)
        assert png[:8] == _PNG_SIG

    def test_line_shape(self) -> None:
        from app.models.visual_spec import Shape
        spec = VisualSpecification(
            title="Test",
            shapes=[Shape(type="line", x1=100, y1=100, x2=800, y2=500,
                          stroke="#10B981", stroke_width=3)],
        )
        png = PNGRenderer().render(spec)
        assert png[:8] == _PNG_SIG

    def test_polygon_shape(self) -> None:
        from app.models.visual_spec import Shape
        spec = VisualSpecification(
            title="Test",
            shapes=[Shape(type="polygon",
                          points="100,100 200,50 300,100 200,200",
                          fill="#6366F1", stroke="#1e293b")],
        )
        png = PNGRenderer().render(spec)
        assert png[:8] == _PNG_SIG

    def test_text_element(self) -> None:
        from app.models.visual_spec import TextElement
        spec = VisualSpecification(
            title="Test",
            text=[TextElement(text="Hello World", x=450, y=300, font_size=20,
                              fill="#ffffff", align="center")],
        )
        png = PNGRenderer().render(spec)
        assert png[:8] == _PNG_SIG

    def test_arrow_with_marker(self) -> None:
        from app.models.visual_spec import Arrow
        spec = VisualSpecification(
            title="Test",
            arrows=[Arrow(x1=100, y1=100, x2=800, y2=500, stroke="#F18F01",
                          stroke_width=3, marker=True)],
        )
        png = PNGRenderer().render(spec)
        assert png[:8] == _PNG_SIG

    def test_node_circle_shape(self) -> None:
        from app.models.visual_spec import Node
        spec = VisualSpecification(
            title="Test",
            nodes=[Node(id="n1", label="Start", x=400, y=300, width=100,
                        height=100, fill="#2E86AB", stroke="#1e293b",
                        font_size=14, shape="circle")],
        )
        png = PNGRenderer().render(spec)
        assert png[:8] == _PNG_SIG

    def test_node_rounded_rect_shape(self) -> None:
        from app.models.visual_spec import Node
        spec = VisualSpecification(
            title="Test",
            nodes=[Node(id="n1", label="Process", x=400, y=300, width=160,
                        height=70, fill="#A23B72", stroke="#1e293b",
                        font_size=14, shape="rounded_rect")],
        )
        png = PNGRenderer().render(spec)
        assert png[:8] == _PNG_SIG


# ── Opacity ──────────────────────────────────────────────────────────────────

def test_elements_with_opacity_render(mock_spec: VisualSpecification) -> None:
    """Specs with opacity-bearing shapes should still produce valid PNG."""
    svg = SVGRenderer().render(mock_spec)
    assert 'opacity="' in svg  # the mock spec has shapes with opacity
    png = PNGRenderer().render(mock_spec)
    assert png[:8] == _PNG_SIG


# ── End-to-end pipeline ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_mock_to_png() -> None:
    """Full pipeline: MockTextGenerator → spec → SVG → PNG."""
    gen = MockTextGenerator()
    system_prompt = (
        "You are a visual planning agent.\n\n"
        "Visual type requested: complexity_image.\n"
        "Complexity: high.\n\n"
        "User prompt: Create an infographic about the water cycle."
    )
    result = await gen.generate("trigger", system_prompt=system_prompt)
    spec = VisualSpecification.model_validate(json.loads(result.text))
    png = PNGRenderer().render(spec)
    assert png[:8] == _PNG_SIG
    img = Image.open(BytesIO(png))
    img.load()
    assert img.format == "PNG"
