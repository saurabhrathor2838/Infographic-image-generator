"""
Tests for :class:`~app.critics.quality_critic.VisualQualityCritic`.

Covers all nine check categories:
  1.  VisualSpecification validity
  2.  Text overflow / out-of-bounds elements
  3.  Element overlap
  4.  Missing or empty content
  5.  Invalid SVG
  6.  Broken connections / arrows
  7.  Complexity-level mismatch
  8.  Template mismatch
  9.  Minimum spacing / layout rules

Also verifies the QualityReport structure (passed, score, issues, warnings,
suggestions) and end-to-end integration with the TemplateEngine + SVGRenderer.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from app.critics.quality_critic import VisualQualityCritic
from app.models.quality_report import QualityReport
from app.models.visual_spec import (
    Arrow,
    Connection,
    Layout,
    Node,
    Section,
    Shape,
    ShapeType,
    TextElement,
    TextAlign,
    VisualSpecification,
)
from app.renderers.svg_renderer import SVGRenderer
from app.templates.engine import TemplateEngine

_P = "Create a diagram about the software development lifecycle."


# ── Helper to build specs quickly ─────────────────────────────────────────────


def _mk_spec(**kwargs) -> VisualSpecification:
    """Create a minimal valid spec with sensible defaults."""
    defaults = dict(
        title="Process Flow",
        layout=Layout(width=900, height=650, background="#0f172a", padding=40),
        title_font_size=36,
        title_fill="#ffffff",
        sections=[],
        text=[],
        shapes=[],
        arrows=[],
        nodes=[
            Node(id="n1", label="Input", x=100, y=280, width=180, height=80, fill="#2E86AB"),
            Node(id="n2", label="Output", x=400, y=280, width=180, height=80, fill="#A23B72"),
        ],
        connections=[Connection(source="n1", target="n2")],
    )
    defaults.update(kwargs)
    return VisualSpecification(**defaults)


# ── QualityReport model ──────────────────────────────────────────────────────


class TestQualityReport:
    def test_defaults(self) -> None:
        r = QualityReport(passed=True, score=100.0)
        assert r.issues == []
        assert r.warnings == []
        assert r.suggestions == []

    def test_add_methods(self) -> None:
        r = QualityReport(passed=True, score=100.0)
        r.add_issue("bad")
        r.add_warning("meh")
        r.add_suggestion("maybe")
        assert r.issues == ["bad"]
        assert r.warnings == ["meh"]
        assert r.suggestions == ["maybe"]

    def test_finalize_no_findings(self) -> None:
        r = QualityReport(passed=True, score=100.0)
        r.finalize()
        assert r.passed is True
        assert r.score == 100.0

    def test_finalize_with_issues(self) -> None:
        r = QualityReport(passed=True, score=100.0)
        r.add_issue("critical")
        r.add_warning("warn")
        r.add_suggestion("suggest")
        r.finalize()
        assert r.passed is False
        # 100 - 25*1 - 5*1 - 2*1 = 68
        assert r.score == 68.0

    def test_finalize_score_clamped_to_zero(self) -> None:
        r = QualityReport(passed=True, score=100.0)
        for _ in range(10):
            r.add_issue("critical")
        r.finalize()
        assert r.score == 0.0
        assert r.passed is False

    def test_finalize_multiple_issues(self) -> None:
        r = QualityReport(passed=True, score=100.0)
        r.add_issue("i1")
        r.add_issue("i2")
        r.add_warning("w1")
        r.add_warning("w2")
        r.add_warning("w3")
        r.add_suggestion("s1")
        r.finalize()
        # 100 - 25*2 - 5*3 - 2*1 = 100 - 50 - 15 - 2 = 33
        assert r.score == 33.0


# ── 1. Spec validity ─────────────────────────────────────────────────────────


class TestSpecValidity:
    def test_valid_spec_passes(self) -> None:
        critic = VisualQualityCritic()
        report = critic.critique(_mk_spec())
        assert report.passed is True
        assert len(report.issues) == 0

    def test_non_positive_dimensions(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec()
        spec.layout = Layout.model_construct(width=0, height=650, background="#0f172a", padding=40)
        report = critic.critique(spec)
        assert any("non-positive" in i for i in report.issues)

    def test_negative_padding(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec()
        spec.layout = Layout.model_construct(width=900, height=650, background="#0f172a", padding=-10)
        report = critic.critique(spec)
        assert any("negative" in i.lower() for i in report.issues)

    def test_title_font_size_zero(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec()
        # Bypass Pydantic validation to test the critic's own check
        spec.title_font_size = 0
        report = critic.critique(spec)
        assert any("font size" in i.lower() for i in report.issues)


# ── 2. Out-of-bounds elements ────────────────────────────────────────────────


class TestOutOfBounds:
    def test_node_out_of_bounds(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            nodes=[Node(id="n1", label="A", x=-50, y=280, width=100, height=60, fill="#fff")],
            connections=[],
        )
        report = critic.critique(spec)
        assert any("out of canvas" in i for i in report.issues)

    def test_shape_out_of_bounds(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            nodes=[],
            shapes=[Shape(type=ShapeType.RECT, x=1000, y=500, width=200, height=100, fill="#fff")],
            connections=[],
        )
        report = critic.critique(spec)
        assert any("out of canvas" in i for i in report.issues)

    def test_arrow_out_of_bounds(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            arrows=[Arrow(x1=0, y1=0, x2=1000, y2=0, marker=True)],
        )
        report = critic.critique(spec)
        assert any("Arrow 0" in w and "bounds" in w.lower() for w in report.warnings)

    def test_text_near_edge_is_warning(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            text=[TextElement(text="edge", x=35, y=600, font_size=16, fill="#fff", align=TextAlign.CENTER)],
        )
        report = critic.critique(spec)
        assert any("near the canvas edge" in w for w in report.warnings)

    def test_section_out_of_bounds(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            sections=[Section(title="S", x=850, y=50, width=200, height=100, fill="#fff")],
        )
        report = critic.critique(spec)
        assert any("out of canvas" in i for i in report.issues)


# ── 3. Element overlap ───────────────────────────────────────────────────────


class TestElementOverlap:
    def test_overlapping_nodes_warned(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            nodes=[
                Node(id="n1", label="A", x=100, y=280, width=200, height=80, fill="#2E86AB"),
                Node(id="n2", label="B", x=150, y=300, width=200, height=80, fill="#A23B72"),
            ],
            connections=[],
        )
        report = critic.critique(spec)
        assert any("overlap" in w.lower() for w in report.warnings)

    def test_non_overlapping_nodes_ok(self) -> None:
        critic = VisualQualityCritic()
        report = critic.critique(_mk_spec())
        assert not any("overlap" in w.lower() for w in report.warnings)

    def test_overlapping_shapes_warned(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            nodes=[],
            shapes=[
                Shape(type=ShapeType.RECT, x=100, y=200, width=200, height=100, fill="#fff"),
                Shape(type=ShapeType.RECT, x=120, y=220, width=200, height=100, fill="#fff"),
            ],
            connections=[],
        )
        report = critic.critique(spec)
        assert any("overlap" in w.lower() for w in report.warnings)


# ── 4. Missing / empty content ──────────────────────────────────────────────


class TestEmptyContent:
    def test_totally_empty_spec(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            nodes=[], shapes=[], text=[], arrows=[],
            connections=[], sections=[],
        )
        report = critic.critique(spec)
        assert any("no nodes" in i for i in report.issues)
        assert any("no shapes" in w for w in report.warnings)
        assert any("no text" in w for w in report.warnings)

    def test_empty_text_element(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            text=[TextElement(text=" ", x=100, y=100, font_size=16, fill="#fff", align=TextAlign.CENTER)],
        )
        report = critic.critique(spec)
        assert any("empty or whitespace" in i for i in report.issues)

    def test_node_with_empty_label(self) -> None:
        critic = VisualQualityCritic()
        node = Node.model_construct(
            id="n1", label="", x=100, y=280, width=100, height=60, fill="#fff"
        )
        spec = _mk_spec(nodes=[node], connections=[])
        report = critic.critique(spec)
        assert any("empty label" in i for i in report.issues)

    def test_no_connections_warning(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(connections=[], arrows=[])
        report = critic.critique(spec)
        assert any("no arrows or connections" in w for w in report.warnings)


# ── 5. Invalid SVG ───────────────────────────────────────────────────────────


class TestSvgValidity:
    def test_valid_svg_passes(self) -> None:
        svg = SVGRenderer().render(_mk_spec())
        critic = VisualQualityCritic()
        report = critic.critique(_mk_spec(), svg=svg)
        assert report.passed is True
        assert not any("SVG" in i for i in report.issues)

    def test_empty_svg(self) -> None:
        critic = VisualQualityCritic()
        report = critic.critique(_mk_spec(), svg="   ")
        assert any("SVG document is empty" in i for i in report.issues)

    def test_malformed_svg(self) -> None:
        critic = VisualQualityCritic()
        svg = "<svg><rect></svg>"  # missing closing tag for rect (still valid XML actually)
        # Use truly broken XML
        svg = "<svg><text>unclosed"
        report = critic.critique(_mk_spec(), svg=svg)
        assert any("not well-formed" in i for i in report.issues)

    def test_svg_wrong_root(self) -> None:
        critic = VisualQualityCritic()
        svg = "<div>hello</div>"
        report = critic.critique(_mk_spec(), svg=svg)
        assert any("does not start" in i or "root element" in i for i in report.issues)

    def test_svg_missing_closing_tag(self) -> None:
        critic = VisualQualityCritic()
        svg = "<svg><rect/></svg"
        report = critic.critique(_mk_spec(), svg=svg)
        assert any("not well-formed" in i or "does not end" in i for i in report.issues)

    def test_svg_title_mismatch(self) -> None:
        critic = VisualQualityCritic()
        svg = SVGRenderer().render(_mk_spec(title="Process Flow"))
        report = critic.critique(_mk_spec(title="Different Title"), svg=svg)
        assert any("title" in w.lower() for w in report.warnings)


# ── 6. Broken connections / arrows ────────────────────────────────────────────


class TestBrokenConnections:
    def test_connection_to_missing_node(self) -> None:
        critic = VisualQualityCritic()
        spec = VisualSpecification.model_construct(
            title="Process Flow",
            layout=Layout(width=900, height=650, background="#0f172a", padding=40),
            title_font_size=36,
            title_fill="#ffffff",
            sections=[],
            text=[],
            shapes=[],
            arrows=[],
            nodes=[Node(id="n1", label="A", x=100, y=280, width=100, height=60, fill="#fff")],
            connections=[Connection(source="n1", target="nonexistent")],
        )
        report = critic.critique(spec)
        assert any("missing target node" in i for i in report.issues)

    def test_connection_from_missing_node(self) -> None:
        critic = VisualQualityCritic()
        spec = VisualSpecification.model_construct(
            title="Process Flow",
            layout=Layout(width=900, height=650, background="#0f172a", padding=40),
            title_font_size=36,
            title_fill="#ffffff",
            sections=[],
            text=[],
            shapes=[],
            arrows=[],
            nodes=[Node(id="n2", label="B", x=400, y=280, width=100, height=60, fill="#fff")],
            connections=[Connection(source="ghost", target="n2")],
        )
        report = critic.critique(spec)
        assert any("missing source node" in i for i in report.issues)

    def test_self_loop_warning(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            nodes=[Node(id="n1", label="A", x=100, y=280, width=100, height=60, fill="#fff")],
            connections=[Connection(source="n1", target="n1")],
        )
        report = critic.critique(spec)
        assert any("self-loop" in w for w in report.warnings)

    def test_duplicate_connection(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            connections=[
                Connection(source="n1", target="n2"),
                Connection(source="n1", target="n2"),
            ],
        )
        report = critic.critique(spec)
        assert any("duplicate" in w.lower() for w in report.warnings)

    def test_valid_connections_pass(self) -> None:
        critic = VisualQualityCritic()
        report = critic.critique(_mk_spec())
        assert not any("missing" in i for i in report.issues)

    def test_zero_length_arrow(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            arrows=[Arrow(x1=100, y1=200, x2=100, y2=200, marker=True)],
        )
        report = critic.critique(spec)
        assert any("zero length" in i for i in report.issues)


# ── 7. Complexity mismatch ───────────────────────────────────────────────────


class TestComplexityMismatch:
    def test_correct_complexity_passes(self) -> None:
        critic = VisualQualityCritic()
        spec = TemplateEngine.generate(_P, "process_flow", "high")
        report = critic.critique(spec, expected_complexity="high")
        assert not any("complexity range" in w for w in report.warnings)

    def test_low_spec_when_high_expected(self) -> None:
        critic = VisualQualityCritic()
        spec = TemplateEngine.generate(_P, "process_flow", "low")
        report = critic.critique(spec, expected_complexity="high")
        assert any("complexity range" in w for w in report.warnings)

    def test_high_spec_when_low_expected(self) -> None:
        critic = VisualQualityCritic()
        spec = TemplateEngine.generate(_P, "process_flow", "high")
        report = critic.critique(spec, expected_complexity="low")
        assert any("complexity range" in w for w in report.warnings)

    def test_density_suggestion(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(nodes=[], shapes=[], text=[], connections=[], arrows=[])
        report = critic.critique(spec)
        # Sparse spec → suggestion
        assert any("sparse" in s.lower() or "low" in s.lower() for s in report.suggestions)

    def test_density_suggestion_dense(self) -> None:
        critic = VisualQualityCritic()
        nodes = [
            Node(id=f"n{i+1}", label=f"N{i+1}", x=100 + i * 60, y=200, width=40, height=40, fill="#fff")
            for i in range(15)
        ]
        spec = _mk_spec(nodes=nodes, shapes=[Shape(type=ShapeType.RECT, x=50, y=50, width=100, height=50, fill="#fff") for _ in range(15)])
        report = critic.critique(spec)
        assert any("dense" in s.lower() for s in report.suggestions)


# ── 8. Template mismatch ─────────────────────────────────────────────────────


class TestTemplateMismatch:
    def test_matching_template_no_suggestion(self) -> None:
        critic = VisualQualityCritic()
        spec = TemplateEngine.generate("water cycle diagram", "cycle", "medium")
        report = critic.critique(spec, prompt="Explain the water cycle and its stages")
        assert not any("Template mismatch" in s for s in report.suggestions)

    def test_mismatch_detected(self) -> None:
        critic = VisualQualityCritic()
        # Generate a cycle spec but claim the prompt is about a timeline
        spec = TemplateEngine.generate("timeline of events", "cycle", "medium")
        report = critic.critique(spec, prompt="Timeline of historical events from 1900 to 2000")
        assert any("Template mismatch" in s for s in report.suggestions)

    def test_no_template_detected_suggestion(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(title="My Custom Title")
        report = critic.critique(spec, prompt="some random prompt")
        assert any("Could not determine" in s for s in report.suggestions)


# ── 9. Minimum spacing / layout ──────────────────────────────────────────────


class TestMinSpacing:
    def test_nodes_too_close(self) -> None:
        critic = VisualQualityCritic()
        spec = _mk_spec(
            nodes=[
                Node(id="n1", label="A", x=100, y=300, width=100, height=60, fill="#fff"),
                Node(id="n2", label="B", x=105, y=300, width=100, height=60, fill="#fff"),
            ],
            connections=[Connection(source="n1", target="n2")],
        )
        report = critic.critique(spec)
        assert any("too close" in w.lower() for w in report.warnings)

    def test_nodes_spaced_well(self) -> None:
        critic = VisualQualityCritic()
        report = critic.critique(_mk_spec())
        assert not any("too close" in w.lower() for w in report.warnings)


# ── End-to-end: TemplateEngine + SVGRenderer ─────────────────────────────────


class TestEndToEnd:
    """Run the critic on specs generated by every template at every complexity."""

    @pytest.mark.parametrize("template_name", TemplateEngine.available_templates())
    @pytest.mark.parametrize("complexity", ["low", "medium", "high"])
    def test_critique_all_templates(self, template_name: str, complexity: str) -> None:
        spec = TemplateEngine.generate(_P, template_name, complexity)
        svg = SVGRenderer().render(spec)
        critic = VisualQualityCritic()
        report = critic.critique(spec, svg=svg, prompt=_P, expected_complexity=complexity)
        assert isinstance(report, QualityReport)
        assert 0.0 <= report.score <= 100.0

    @pytest.mark.parametrize("template_name", TemplateEngine.available_templates())
    def test_critique_no_svg(self, template_name: str) -> None:
        """Critique should work without an SVG string."""
        spec = TemplateEngine.generate(_P, template_name, "medium")
        critic = VisualQualityCritic()
        report = critic.critique(spec, prompt=_P)
        assert isinstance(report, QualityReport)

    def test_high_score_on_clean_spec(self) -> None:
        """A well-formed spec from the engine should score high."""
        prompt = "Data processing workflow steps"
        spec = TemplateEngine.generate(prompt, "process_flow", "medium")
        svg = SVGRenderer().render(spec)
        critic = VisualQualityCritic()
        report = critic.critique(spec, svg=svg, prompt=prompt, expected_complexity="medium")
        # Should pass with a score >= 90 (minor layout warnings are acceptable)
        assert report.passed is True
        assert report.score >= 90.0

    def test_score_decreases_with_issues(self) -> None:
        """Adding issues should lower the score."""
        clean_spec = _mk_spec()
        critic = VisualQualityCritic()
        clean_report = critic.critique(clean_spec)

        broken_spec = _mk_spec(
            nodes=[],
            shapes=[],
            text=[],
            arrows=[],
            connections=[],
        )
        broken_report = critic.critique(broken_spec)
        assert broken_report.score < clean_report.score
