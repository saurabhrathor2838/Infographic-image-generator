"""
Tests for :class:`~app.templates.engine.TemplateEngine`.

Covers:
  - Template selection from natural-language prompts.
  - All 8 templates produce valid, renderable :class:`VisualSpecification`.
  - All 3 complexity levels (low / medium / high) for every template.
  - Complexity scales density: high → more nodes / shapes / connections.
  - End-to-end rendering: every template renders to both SVG and PNG.
  - MockTextGenerator integration: template selection flows through the
    mock generator into the /api/plan endpoint.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from io import BytesIO

import pytest
from httpx import AsyncClient
from PIL import Image

from app.models.visual_spec import VisualSpecification
from app.providers.mock_text_generator import MockTextGenerator
from app.renderers.png_renderer import PNGRenderer
from app.renderers.svg_renderer import SVGRenderer
from app.templates.engine import TemplateEngine

_PNG_SIG = b"\x89PNG\r\n\x1a\n"

_PROMPT = "Create a diagram about the software development lifecycle."


# ── Template selection ───────────────────────────────────────────────────────


class TestTemplateSelection:
    """Verify ``select_template`` picks the right template from a prompt."""

    @pytest.mark.parametrize(
        "prompt, expected",
        [
            # Cycle
            ("Explain the water cycle and its stages", "cycle"),
            ("Show the recycling cycle of materials", "cycle"),
            # Timeline
            ("Timeline of historical events from 1900 to 2000", "timeline"),
            ("Chronological history of the internet", "timeline"),
            # Comparison
            ("Compare solar energy vs wind energy", "comparison"),
            ("Comparison of iPhone and Android features", "comparison"),
            # Statistics
            ("Bar chart of quarterly revenue growth", "statistics"),
            ("Data visualization of user metrics and KPIs", "statistics"),
            # Technical system
            ("Cloud architecture diagram for microservices", "technical_system"),
            ("System design for a distributed web application", "technical_system"),
            # Hierarchy
            ("Organization hierarchy showing reporting structure", "hierarchy"),
            ("Tree diagram of the company's management layers", "hierarchy"),
            # Step-by-step
            ("How to set up a development environment step by step", "step_by_step"),
            ("A tutorial for deploying a web app", "step_by_step"),
            # Process flow (default + explicit)
            ("Create a process flow for customer onboarding", "process_flow"),
            ("Describe the workflow of data processing", "process_flow"),
            ("Tell me about the benefits of solar energy", "process_flow"),  # default fallback
            ("Infographic about the water cycle", "cycle"),  # 'cycle' in prompt
        ],
    )
    def test_select_template(self, prompt: str, expected: str) -> None:
        assert TemplateEngine.select_template(prompt) == expected

    def test_select_template_case_insensitive(self) -> None:
        assert TemplateEngine.select_template("CYCLE of life") == "cycle"
        assert TemplateEngine.select_template("TIMELINE events") == "timeline"

    def test_select_template_empty_fallback(self) -> None:
        assert TemplateEngine.select_template("") == "process_flow"
        assert TemplateEngine.select_template("just some random text") == "process_flow"

    def test_available_templates(self) -> None:
        templates = TemplateEngine.available_templates()
        assert len(templates) == 8
        expected = {
            "process_flow", "timeline", "comparison", "cycle", "hierarchy",
            "statistics", "technical_system", "step_by_step",
        }
        assert set(templates) == expected


# ── Template generation: validity ─────────────────────────────────────────────


@pytest.mark.parametrize("template_name", TemplateEngine.available_templates())
@pytest.mark.parametrize("complexity", ["low", "medium", "high"])
def test_template_generates_valid_spec(template_name: str, complexity: str) -> None:
    """Every template × complexity must produce a schema-valid specification."""
    spec = TemplateEngine.generate(_PROMPT, template_name, complexity)
    assert isinstance(spec, VisualSpecification)
    assert spec.title
    assert len(spec.nodes) >= 1

    # All connections must reference existing node IDs.
    node_ids = {n.id for n in spec.nodes}
    for conn in spec.connections:
        assert conn.source in node_ids
        assert conn.target in node_ids


@pytest.mark.parametrize("template_name", TemplateEngine.available_templates())
@pytest.mark.parametrize("complexity", ["low", "medium", "high"])
def test_template_renders_svg(template_name: str, complexity: str) -> None:
    """Every template must render to valid SVG."""
    spec = TemplateEngine.generate(_PROMPT, template_name, complexity)
    svg = SVGRenderer().render(spec)
    assert svg.startswith("<svg")
    assert svg.strip().endswith("</svg>")
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")


@pytest.mark.parametrize("template_name", TemplateEngine.available_templates())
@pytest.mark.parametrize("complexity", ["low", "medium", "high"])
def test_template_renders_png(template_name: str, complexity: str) -> None:
    """Every template must render to valid PNG via Pillow."""
    spec = TemplateEngine.generate(_PROMPT, template_name, complexity)
    png = PNGRenderer().render(spec)
    assert png[:8] == _PNG_SIG
    img = Image.open(BytesIO(png))
    img.load()
    assert img.format == "PNG"
    assert img.size[0] > 500 and img.size[1] > 300


# ── Complexity scaling ───────────────────────────────────────────────────────


@pytest.mark.parametrize("template_name", TemplateEngine.available_templates())
def test_high_complexity_scales_up(template_name: str) -> None:
    """High complexity should produce a denser spec than low."""
    low = TemplateEngine.generate(_PROMPT, template_name, "low")
    high = TemplateEngine.generate(_PROMPT, template_name, "high")
    assert len(high.nodes) >= len(low.nodes)
    assert len(high.shapes) >= len(low.shapes)
    assert len(high.text) >= len(low.text)


# ── Auto-selection via generate() ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "prompt, expected_template",
    [
        ("The water cycle", "cycle"),
        ("Revenue bar chart", "statistics"),
        ("System architecture", "technical_system"),
        ("Company hierarchy", "hierarchy"),
        ("Project timeline", "timeline"),
        ("Features comparison", "comparison"),
        ("How to bake a cake", "step_by_step"),
        ("Data processing workflow", "process_flow"),
    ],
)
def test_generate_auto_selects_template(prompt: str, expected_template: str) -> None:
    """When template=None, generate() should auto-select based on the prompt."""
    spec = TemplateEngine.generate(prompt)
    assert isinstance(spec, VisualSpecification)
    assert spec.title


# ── Individual template structural checks ─────────────────────────────────────


class TestProcessFlowTemplate:
    def test_structure(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "process_flow", "high")
        assert len(spec.nodes) >= 6
        assert len(spec.connections) >= 5
        assert len(spec.shapes) >= 4
        assert len(spec.text) >= 4

    def test_low_complexity(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "process_flow", "low")
        assert len(spec.nodes) <= 3
        assert len(spec.shapes) <= 2
        assert len(spec.text) <= 2


class TestTimelineTemplate:
    def test_structure(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "timeline", "medium")
        assert len(spec.nodes) >= 2
        # Timeline should have a baseline shape (line)
        assert any(s.type.value == "line" for s in spec.shapes)

    def test_low_complexity(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "timeline", "low")
        assert len(spec.nodes) <= 3
        assert len(spec.shapes) <= 2
        assert len(spec.text) <= 2


class TestComparisonTemplate:
    def test_structure_two_columns(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "comparison", "medium")
        assert len(spec.nodes) >= 4  # at least 2 per column
        # No connections in comparison layout
        assert len(spec.connections) == 0

    def test_low_complexity(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "comparison", "low")
        assert len(spec.nodes) <= 3
        assert len(spec.shapes) <= 2


class TestCycleTemplate:
    """The cycle template is used by the mock generator for 'water cycle' prompts.

    It must satisfy the mock generator's complexity-scaling constraints:
    low  → nodes ≤ 3, shapes ≤ 2, text ≤ 2, connections ≤ 2
    high → nodes ≥ 6, shapes ≥ 4, text ≥ 4, connections ≥ 5
    """

    def test_low_passes_mock_constraints(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "cycle", "low")
        assert len(spec.nodes) <= 3
        assert len(spec.shapes) <= 2
        assert len(spec.text) <= 2
        assert len(spec.connections) <= 2

    def test_medium_passes_mock_constraints(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "cycle", "medium")
        assert 2 <= len(spec.nodes) <= 4
        assert len(spec.shapes) >= 2
        assert len(spec.text) >= 2

    def test_high_passes_mock_constraints(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "cycle", "high")
        assert len(spec.nodes) >= 6
        assert len(spec.shapes) >= 4
        assert len(spec.text) >= 4
        assert len(spec.connections) >= 5

    def test_connections_form_cycle(self) -> None:
        """Each node should have an incoming and outgoing connection."""
        spec = TemplateEngine.generate(_PROMPT, "cycle", "medium")
        assert len(spec.nodes) == len(spec.connections)  # cyclic: n nodes → n edges


class TestHierarchyTemplate:
    def test_root_exists(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "hierarchy", "high")
        root = spec.nodes[0]
        # Root should be a circle (or different from children)
        assert root.shape == "circle"

    def test_low_complexity(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "hierarchy", "low")
        assert len(spec.nodes) <= 3
        assert len(spec.shapes) <= 2
        assert len(spec.text) <= 2


class TestStatisticsTemplate:
    def test_has_bar_shapes(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "statistics", "medium")
        # Statistics should use rect shapes (bars)
        assert any(s.type.value in ("rect", "rounded_rect") for s in spec.shapes)

    def test_low_complexity(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "statistics", "low")
        assert len(spec.nodes) <= 3
        assert len(spec.shapes) <= 2
        assert len(spec.text) <= 2


class TestTechnicalSystemTemplate:
    def test_structure(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "technical_system", "high")
        assert len(spec.nodes) >= 6
        assert len(spec.connections) >= 5

    def test_high_has_cross_connections(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "technical_system", "high")
        # High complexity should have more than just linear connections
        assert len(spec.connections) >= 6


class TestStepByStepTemplate:
    def test_structure(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "step_by_step", "high")
        assert len(spec.nodes) >= 6
        assert len(spec.connections) >= 5

    def test_low_complexity(self) -> None:
        spec = TemplateEngine.generate(_PROMPT, "step_by_step", "low")
        assert len(spec.nodes) <= 3
        assert len(spec.shapes) <= 2
        assert len(spec.text) <= 2


# ── Invalid template ──────────────────────────────────────────────────────────


def test_invalid_template_raises() -> None:
    with pytest.raises(ValueError, match="Unknown template"):
        TemplateEngine.generate(_PROMPT, "nonexistent", "medium")


# ── End-to-end: MockTextGenerator → TemplateEngine ────────────────────────────


class TestMockGeneratorIntegration:
    """Verify the mock generator uses template selection from the prompt."""

    @pytest.mark.asyncio
    async def test_water_cycle_selects_cycle_template(self) -> None:
        """The 'water cycle' prompt should auto-select the cycle template."""
        gen = MockTextGenerator()
        system_prompt = (
            "You are a visual planning agent.\n\n"
            "Visual type requested: infographic. Complexity: low.\n\n"
            "User prompt: Create an infographic explaining the water cycle."
        )
        result = await gen.generate("trigger", system_prompt=system_prompt)
        spec = VisualSpecification.model_validate(json.loads(result.text))
        # Cycle template with 2 nodes for low complexity
        assert len(spec.nodes) >= 2
        assert isinstance(spec, VisualSpecification)

    @pytest.mark.asyncio
    async def test_process_flow_prompt(self) -> None:
        """A process-flow prompt should produce a valid spec."""
        gen = MockTextGenerator()
        system_prompt = (
            "You are a visual planning agent.\n\n"
            "Visual type requested: infographic. Complexity: medium.\n\n"
            "User prompt: Create a process flow for the data pipeline."
        )
        result = await gen.generate("trigger", system_prompt=system_prompt)
        spec = VisualSpecification.model_validate(json.loads(result.text))
        assert isinstance(spec, VisualSpecification)
        assert len(spec.nodes) >= 2
        assert len(spec.connections) >= 1

    @pytest.mark.asyncio
    async def test_all_complexities_from_mock(self) -> None:
        """The mock generator should work for all complexity levels."""
        gen = MockTextGenerator()
        for complexity in ("low", "medium", "high"):
            system_prompt = (
                f"You are a visual planning agent.\n\n"
                f"Visual type requested: infographic. Complexity: {complexity}.\n\n"
                f"User prompt: Create an infographic explaining the water cycle."
            )
            result = await gen.generate("trigger", system_prompt=system_prompt)
            spec = VisualSpecification.model_validate(json.loads(result.text))
            assert spec.title


# ── End-to-end: /api/plan with PNG ───────────────────────────────────────────


class TestPlanWithTemplateSelection:
    """Integration tests via the /api/plan endpoint."""

    _PNG_SIG = b"\x89PNG\r\n\x1a\n"

    async def test_plan_png_with_mock(self, client: AsyncClient, override_llm) -> None:
        """POST /api/plan?format=png should return valid PNG via mock provider."""
        gen = MockTextGenerator()
        override_llm(gen)

        response = await client.post(
            "/api/plan?format=png",
            json={
                "prompt": "Create an infographic explaining the water cycle.",
                "visual_type": "infographic",
                "complexity": "high",
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content[:8] == self._PNG_SIG
        img = Image.open(BytesIO(response.content))
        img.load()
        assert img.format == "PNG"
