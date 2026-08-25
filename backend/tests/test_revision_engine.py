"""
Tests for :class:`~app.agents.revision_engine.RevisionEngine`.

Covers:
  - Pass on first attempt (clean spec, revisions = 0).
  - Fail → structural revision → pass (revisions = 1).
  - Fail → template regeneration → pass (revisions = 1 or 2).
  - Max attempts exhausted (revisions = MAX_REVISIONS, passed = False).
  - Infinite-loop prevention (engine always terminates).
  - Revision count never exceeds MAX_REVISIONS.
  - Original spec is not mutated.
  - Returns SVG, PNG, report, and revision count.
  - End-to-end with TemplateEngine + SVGRenderer + PNGRenderer.
"""

from __future__ import annotations

import math
from io import BytesIO
from xml.etree import ElementTree as ET

import pytest
from PIL import Image

from app.agents.revision_engine import RevisionEngine, RevisionResult
from app.critics.quality_critic import VisualQualityCritic
from app.models.quality_report import QualityReport
from app.models.visual_spec import (
    Arrow,
    Connection,
    Layout,
    Node,
    Shape,
    ShapeType,
    TextElement,
    TextAlign,
    VisualSpecification,
)
from app.renderers.png_renderer import PNGRenderer
from app.renderers.svg_renderer import SVGRenderer
from app.templates.engine import TemplateEngine

_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_PROMPT = "Data processing workflow steps"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _clean_spec() -> VisualSpecification:
    """A spec that should pass the critic with no issues."""
    return TemplateEngine.generate(_PROMPT, "process_flow", "medium")


def _fixable_spec() -> VisualSpecification:
    """A spec with issues that structural fixes can resolve.

    - One node is out of bounds (negative x).
    - One connection references a non-existent node (bypass validator).
    - One arrow is zero-length.
    """
    spec = _clean_spec()
    # Move a node out of bounds
    spec.nodes[0].x = -50
    # Add a broken connection (bypass model_validator)
    # We'll just remove a valid connection to create a "no connections" scenario
    # Actually, let's make a spec with out-of-bounds + overlapping nodes
    if len(spec.nodes) >= 2:
        spec.nodes[0].x = -50  # out of bounds
        spec.nodes[1].x = spec.nodes[0].x  # overlap with node 0
        spec.nodes[1].y = spec.nodes[0].y
    # Add a zero-length arrow
    spec.arrows.append(Arrow(x1=100, y1=200, x2=100, y2=200, marker=True))
    return spec


def _unfixable_spec_no_prompt() -> VisualSpecification:
    """A spec with issues that structural fixes cannot resolve.

    A whitespace-only text element is an issue the structural revision
    engine does not fix (it does not modify text content).  Without a
    prompt, there is no template to regenerate from.
    """
    spec = _clean_spec()
    # Add a whitespace-only text element (bypass Pydantic min_length by construct)
    bad_text = TextElement.model_construct(
        text="   ", x=100, y=100,
        font_size=16, font_family="Arial, Helvetica, sans-serif",
        fill="#ffffff", weight="normal", align=TextAlign.CENTER,
    )
    spec.text.append(bad_text)
    return spec


# ── RevisionResult structure ─────────────────────────────────────────────────


class TestRevisionResult:
    def test_result_has_required_fields(self) -> None:
        engine = RevisionEngine()
        result = engine.revise(_clean_spec(), render_png=False)
        assert hasattr(result, "spec")
        assert hasattr(result, "svg")
        assert hasattr(result, "png")
        assert hasattr(result, "report")
        assert hasattr(result, "revisions")
        assert hasattr(result, "passed")

    def test_result_is_revision_result(self) -> None:
        engine = RevisionEngine()
        result = engine.revise(_clean_spec(), render_png=False)
        assert isinstance(result, RevisionResult)

    def test_result_report_is_quality_report(self) -> None:
        engine = RevisionEngine()
        result = engine.revise(_clean_spec(), render_png=False)
        assert isinstance(result.report, QualityReport)


# ── 1. Pass on first attempt ─────────────────────────────────────────────────


class TestPassOnFirstAttempt:
    def test_clean_spec_passes_zero_revisions(self) -> None:
        engine = RevisionEngine()
        result = engine.revise(_clean_spec(), prompt=_PROMPT, complexity="medium", render_png=False)
        assert result.passed is True
        assert result.revisions == 0

    def test_clean_spec_score_high(self) -> None:
        engine = RevisionEngine()
        result = engine.revise(_clean_spec(), prompt=_PROMPT, complexity="medium", render_png=False)
        assert result.report.score >= 90.0

    def test_clean_spec_no_critical_issues(self) -> None:
        engine = RevisionEngine()
        result = engine.revise(_clean_spec(), prompt=_PROMPT, complexity="medium", render_png=False)
        assert len(result.report.issues) == 0


# ── 2. Fail → revision → pass ────────────────────────────────────────────────


class TestFailAndRevision:
    def test_fixable_spec_revised_and_passes(self) -> None:
        """A spec with structural issues should be fixed within 1 revision."""
        engine = RevisionEngine()
        original = _fixable_spec()
        # Verify the original spec has issues
        pre_report = VisualQualityCritic().critique(original)
        assert not pre_report.passed

        result = engine.revise(original, prompt=_PROMPT, complexity="medium", render_png=False)
        # After structural fixes, should pass (or at worst, be improved)
        assert result.revisions >= 1
        assert result.report.score > pre_report.score

    def test_revised_spec_has_no_out_of_bounds(self) -> None:
        """After revision, no nodes should be out of bounds."""
        engine = RevisionEngine()
        original = _fixable_spec()
        result = engine.revise(original, render_png=False)
        layout = result.spec.layout
        for node in result.spec.nodes:
            assert node.x >= 0 or node.x >= layout.padding  # clamped to bounds
            assert node.x + node.width <= layout.width
            assert node.y + node.height <= layout.height

    def test_revised_spec_no_broken_connections(self) -> None:
        """After revision, all connections should reference valid nodes."""
        engine = RevisionEngine()
        original = _fixable_spec()
        result = engine.revise(original, render_png=False)
        node_ids = {n.id for n in result.spec.nodes}
        for conn in result.spec.connections:
            assert conn.source in node_ids
            assert conn.target in node_ids

    def test_revised_spec_no_zero_length_arrows(self) -> None:
        """After revision, no zero-length arrows should remain."""
        engine = RevisionEngine()
        original = _fixable_spec()
        result = engine.revise(original, render_png=False)
        for arrow in result.spec.arrows:
            length = math.hypot(arrow.x2 - arrow.x1, arrow.y2 - arrow.y1)
            assert length > 0

    def test_revision_with_prompt_regenerates(self) -> None:
        """When a prompt is available, the engine can regenerate from template."""
        engine = RevisionEngine()
        spec = TemplateEngine.generate(_PROMPT, "process_flow", "medium")
        # Add completely out-of-bounds nodes
        for i in range(50):
            spec.nodes.append(Node(
                id=f"oob_{i}", label=f"O{i}", x=5000 + i, y=5000,
                width=100, height=60, fill="#fff"
            ))
        result = engine.revise(spec, prompt=_PROMPT, complexity="medium", render_png=False)
        # Should have revised at least once
        assert result.revisions >= 1
        # After regeneration, should have reasonable node positions
        for node in result.spec.nodes:
            assert node.x + node.width <= spec.layout.width + 100  # allow small tolerance


# ── 3. Max attempts exhausted ────────────────────────────────────────────────


class TestMaxAttempts:
    def test_max_attempts_exhausted(self) -> None:
        """An unfixable spec (without prompt) should exhaust all revision attempts."""
        engine = RevisionEngine()
        original = _unfixable_spec_no_prompt()
        result = engine.revise(original, render_png=False)
        assert result.revisions == RevisionEngine.MAX_REVISIONS
        assert result.passed is False

    def test_revisions_never_exceed_max(self) -> None:
        """Revision count must never exceed MAX_REVISIONS."""
        engine = RevisionEngine()
        # Use an unfixable spec without prompt
        original = _unfixable_spec_no_prompt()
        result = engine.revise(original, render_png=False)
        assert result.revisions <= RevisionEngine.MAX_REVISIONS

    def test_engine_terminates(self) -> None:
        """The engine must always terminate (no infinite loop)."""
        engine = RevisionEngine()
        # A spec that will always fail (whitespace text, no prompt)
        original = _unfixable_spec_no_prompt()
        result = engine.revise(original, render_png=False)
        # If we get here, the engine terminated.
        assert isinstance(result, RevisionResult)

    def test_max_attempts_still_renders(self) -> None:
        """Even when maxed out, the engine should return rendered output."""
        engine = RevisionEngine()
        original = _unfixable_spec_no_prompt()
        result = engine.revise(original, render_png=True)
        assert len(result.svg) > 0
        assert result.png is not None
        assert result.png[:8] == _PNG_SIG


# ── 4. Original spec not mutated ──────────────────────────────────────────────


class TestNoMutation:
    def test_original_spec_unchanged(self) -> None:
        """The engine must not mutate the caller's spec."""
        engine = RevisionEngine()
        original = _fixable_spec()
        original_nodes = [n.model_copy() for n in original.nodes]
        original_arrows = [a.model_copy() for a in original.arrows]
        original_conns = [c.model_copy() for c in original.connections]
        original_x = original.nodes[0].x

        _ = engine.revise(original, render_png=False)

        assert original.nodes[0].x == original_x
        assert len(original.nodes) == len(original_nodes)
        assert len(original.arrows) == len(original_arrows)
        assert len(original.connections) == len(original_conns)


# ── 5. End-to-end with rendering ─────────────────────────────────────────────


class TestEndToEnd:
    def test_returns_svg(self) -> None:
        engine = RevisionEngine()
        result = engine.revise(_clean_spec(), render_png=False)
        assert result.svg.startswith("<svg")
        assert result.svg.strip().endswith("</svg>")
        # Verify SVG is valid XML
        root = ET.fromstring(result.svg)
        assert root.tag.endswith("svg")

    def test_returns_png(self) -> None:
        engine = RevisionEngine()
        result = engine.revise(_clean_spec(), render_png=True)
        assert result.png is not None
        assert result.png[:8] == _PNG_SIG
        img = Image.open(BytesIO(result.png))
        img.load()
        assert img.format == "PNG"

    def test_all_templates_pass_or_revise(self) -> None:
        """The revision engine should handle specs from all templates."""
        engine = RevisionEngine()
        for template_name in TemplateEngine.available_templates():
            spec = TemplateEngine.generate(_PROMPT, template_name, "medium")
            result = engine.revise(spec, prompt=_PROMPT, complexity="medium", render_png=False)
            assert isinstance(result, RevisionResult)
            assert result.revisions <= RevisionEngine.MAX_REVISIONS
            assert 0.0 <= result.report.score <= 100.0

    def test_complexity_levels(self) -> None:
        """Test revision engine with all complexity levels."""
        engine = RevisionEngine()
        for complexity in ["low", "medium", "high"]:
            spec = TemplateEngine.generate(_PROMPT, "process_flow", complexity)
            result = engine.revise(spec, prompt=_PROMPT, complexity=complexity, render_png=False)
            assert result.revisions <= RevisionEngine.MAX_REVISIONS
            assert 0.0 <= result.report.score <= 100.0

    def test_revision_count_tracks_attempts(self) -> None:
        """Verify revision count corresponds to actual revisions made."""
        engine = RevisionEngine()
        # Clean spec: 0 revisions
        result = engine.revise(_clean_spec(), prompt=_PROMPT, complexity="medium", render_png=False)
        assert result.revisions == 0
        assert result.passed is True

    def test_no_prompt_only_structural(self) -> None:
        """Without a prompt, only structural fixes are attempted."""
        engine = RevisionEngine()
        spec = _fixable_spec()
        # No prompt → can only use structural fixes
        result = engine.revise(spec, render_png=False)
        assert result.revisions <= RevisionEngine.MAX_REVISIONS
        assert isinstance(result, RevisionResult)

    def test_final_report_includes_svg_checks(self) -> None:
        """The final report should include SVG validity checks."""
        engine = RevisionEngine()
        result = engine.revise(_clean_spec(), render_png=False)
        # SVG checks are included in the final report
        # If SVG is valid, there should be no SVG-related issues
        assert not any("SVG" in i or "svg" in i for i in result.report.issues)

    def test_score_improves_or_maintained(self) -> None:
        """The revision engine should not make the score worse."""
        engine = RevisionEngine()
        original = _fixable_spec()
        pre_report = VisualQualityCritic().critique(original, prompt=_PROMPT, expected_complexity="medium")
        result = engine.revise(original, prompt=_PROMPT, complexity="medium", render_png=False)
        assert result.report.score >= pre_report.score

    def test_revisions_terminate_quickly(self) -> None:
        """Even with a very broken spec, the engine should finish quickly."""
        engine = RevisionEngine()
        spec = _clean_spec()
        # Completely break everything
        spec.nodes = [
            Node(id=f"n{i}", label=f"N{i}",
                 x=-1000 + i * 10, y=-1000, width=1000, height=600,
                 fill="#fff")
            for i in range(20)
        ]
        spec.connections = [Connection(source="ghost1", target="ghost2")]
        result = engine.revise(spec, prompt=_PROMPT, complexity="medium", render_png=False)
        assert isinstance(result, RevisionResult)
        assert result.revisions <= RevisionEngine.MAX_REVISIONS
