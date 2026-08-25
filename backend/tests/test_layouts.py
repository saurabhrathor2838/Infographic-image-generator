"""
Tests for :class:`~app.renderers.layouts.LayoutEngine`.

Covers:
  - All six layout types produce schema-valid :class:`VisualSpecification`.
  - All three complexity levels (low / medium / high) are accepted.
  - Complexity scales density: high → more nodes / shapes / connections.
  - ``generate()`` dispatches to the correct method.
  - Invalid layout names raise ``ValueError``.
  - ``available_layouts()`` returns all six names.
"""

from __future__ import annotations

import pytest

from app.models.visual_spec import VisualSpecification
from app.renderers.layouts import LayoutEngine
from app.renderers.png_renderer import PNGRenderer

_PROMPT = "Create a diagram about the software development lifecycle."


# ── Layout dispatch ──────────────────────────────────────────────────────────

class TestLayoutDispatch:
    """Test the ``generate`` dispatcher."""

    def test_available_layouts(self) -> None:
        layouts = LayoutEngine.available_layouts()
        assert len(layouts) == 6
        assert "process_flow" in layouts
        assert "timeline" in layouts
        assert "comparison" in layouts
        assert "hierarchy" in layouts
        assert "cycle" in layouts
        assert "technical_diagram" in layouts

    @pytest.mark.parametrize("layout_name", LayoutEngine.available_layouts())
    def test_generate_returns_valid_spec(self, layout_name: str) -> None:
        spec = LayoutEngine.generate(_PROMPT, layout_name, "medium")
        assert isinstance(spec, VisualSpecification)
        assert spec.title
        assert len(spec.nodes) >= 1

    def test_invalid_layout_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown layout"):
            LayoutEngine.generate(_PROMPT, "nonexistent", "medium")


# ── Per-layout, per-complexity validity ────────────────────────────────────────

@pytest.mark.parametrize("layout_name", LayoutEngine.available_layouts())
@pytest.mark.parametrize("complexity", ["low", "medium", "high"])
def test_layout_complexity_validity(
    layout_name: str, complexity: str
) -> None:
    """Every layout × complexity must produce a valid, renderable spec."""
    spec = LayoutEngine.generate(_PROMPT, layout_name, complexity)
    assert isinstance(spec, VisualSpecification)

    # Must have at least one node.
    assert len(spec.nodes) >= 1, (
        f"{layout_name}/{complexity}: expected >= 1 node, got {len(spec.nodes)}"
    )

    # All connections must reference existing node ids.
    node_ids = {n.id for n in spec.nodes}
    for conn in spec.connections:
        assert conn.source in node_ids, (
            f"{layout_name}/{complexity}: connection source {conn.source!r} "
            f"not in nodes"
        )
        assert conn.target in node_ids, (
            f"{layout_name}/{complexity}: connection target {conn.target!r} "
            f"not in nodes"
        )

    # Must render to PNG without error.
    png = PNGRenderer().render(spec)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


# ── Complexity scaling ────────────────────────────────────────────────────────


class TestComplexityScaling:
    """Verify that higher complexity produces denser specs."""

    @pytest.mark.parametrize("layout_name", LayoutEngine.available_layouts())
    def test_high_has_more_nodes_than_low(self, layout_name: str) -> None:
        low = LayoutEngine.generate(_PROMPT, layout_name, "low")
        high = LayoutEngine.generate(_PROMPT, layout_name, "high")
        assert len(high.nodes) >= len(low.nodes), (
            f"{layout_name}: high ({len(high.nodes)} nodes) should have >= "
            f"as many nodes as low ({len(low.nodes)})"
        )

    @pytest.mark.parametrize("layout_name", LayoutEngine.available_layouts())
    def test_high_has_more_shapes_than_low(self, layout_name: str) -> None:
        low = LayoutEngine.generate(_PROMPT, layout_name, "low")
        high = LayoutEngine.generate(_PROMPT, layout_name, "high")
        assert len(high.shapes) >= len(low.shapes), (
            f"{layout_name}: high ({len(high.shapes)} shapes) should have >= "
            f"as many shapes as low ({len(low.shapes)})"
        )

    @pytest.mark.parametrize("layout_name", LayoutEngine.available_layouts())
    def test_high_has_more_text_than_low(self, layout_name: str) -> None:
        low = LayoutEngine.generate(_PROMPT, layout_name, "low")
        high = LayoutEngine.generate(_PROMPT, layout_name, "high")
        assert len(high.text) >= len(low.text), (
            f"{layout_name}: high ({len(high.text)} text) should have >= "
            f"as many text elements as low ({len(low.text)})"
        )


# ── Layout-specific structural checks ─────────────────────────────────────────


class TestProcessFlow:
    """Process flow: linear chain of nodes with sequential connections."""

    def test_low_has_two_nodes(self) -> None:
        spec = LayoutEngine.process_flow(_PROMPT, "low")
        assert len(spec.nodes) == 2
        assert len(spec.connections) == 1  # n1 → n2

    def test_medium_has_four_nodes(self) -> None:
        spec = LayoutEngine.process_flow(_PROMPT, "medium")
        assert len(spec.nodes) == 4
        assert len(spec.connections) >= 3  # n1→n2→n3→n4

    def test_high_has_six_nodes_and_cross_connections(self) -> None:
        spec = LayoutEngine.process_flow(_PROMPT, "high")
        assert len(spec.nodes) == 6
        # Linear (5) + cross-connections (at least 3 for high)
        assert len(spec.connections) >= 5


class TestTimeline:
    """Timeline: events on a horizontal axis with time labels."""

    def test_low_has_two_events(self) -> None:
        spec = LayoutEngine.timeline(_PROMPT, "low")
        assert len(spec.nodes) == 2
        # Time labels (T0, T1) + footer text
        assert len(spec.text) >= 3

    def test_high_has_seven_text_elements(self) -> None:
        spec = LayoutEngine.timeline(_PROMPT, "medium")
        assert len(spec.nodes) == 4
        # Time labels + annotations + footer
        assert len(spec.text) >= 5


class TestComparison:
    """Comparison: two columns of items with a divider."""

    def test_low_has_four_nodes(self) -> None:
        spec = LayoutEngine.comparison(_PROMPT, "low")
        assert len(spec.nodes) == 4  # 2 per column × 2
        # No connections in comparison layout
        assert len(spec.connections) == 0

    def test_high_has_eight_nodes(self) -> None:
        spec = LayoutEngine.comparison(_PROMPT, "high")
        assert len(spec.nodes) == 8  # 4 per column × 2


class TestHierarchy:
    """Hierarchy: tree structure."""

    def test_low_has_three_nodes(self) -> None:
        spec = LayoutEngine.hierarchy(_PROMPT, "low")
        assert len(spec.nodes) == 3  # root + 2 children
        assert len(spec.connections) == 2  # root → each child

    def test_medium_has_seven_nodes(self) -> None:
        spec = LayoutEngine.hierarchy(_PROMPT, "medium")
        assert len(spec.nodes) == 7  # root + 2 children + 4 grandchildren


class TestCycle:
    """Cycle: circular arrangement."""

    def test_low_has_three_nodes(self) -> None:
        spec = LayoutEngine.cycle(_PROMPT, "low")
        assert len(spec.nodes) == 3
        # Each node connects to the next, forming a cycle
        assert len(spec.connections) == 3

    def test_high_has_seven_nodes(self) -> None:
        spec = LayoutEngine.cycle(_PROMPT, "high")
        assert len(spec.nodes) == 7
        assert len(spec.connections) == 7  # cyclic


class TestTechnicalDiagram:
    """Technical diagram: grid of components with data flow."""

    def test_low_has_two_or_more_nodes(self) -> None:
        spec = LayoutEngine.technical_diagram(_PROMPT, "low")
        assert len(spec.nodes) >= 2
        assert len(spec.connections) >= 1

    def test_high_has_seven_nodes(self) -> None:
        spec = LayoutEngine.technical_diagram(_PROMPT, "high")
        assert len(spec.nodes) == 7
        # Dense connections: linear + cross-connections
        assert len(spec.connections) >= 6
