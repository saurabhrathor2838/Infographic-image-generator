"""
Reusable layout engine for :class:`~app.models.visual_spec.VisualSpecification`.

Provides six ready-made diagram layouts that can be used by the mock generator,
the VisualPlannerAgent, or any future agent to produce structured specs:

* **process flow**   — sequential steps connected by arrows.
* **timeline**       — events laid out along a horizontal time axis.
* **comparison**     — two columns of items for side-by-side comparison.
* **hierarchy**      — a tree structure with parent-to-child connections.
* **cycle**          — nodes arranged in a circle with a cyclic flow.
* **technical diagram** — components with data-flow arrows (dense, detailed).

Every layout accepts a ``complexity`` parameter (``"low"``, ``"medium"``,
``"high"``) and scales node count, shape count, connection density and
annotation text accordingly.

All layouts return a validated :class:`VisualSpecification` — no AI image
generation API is used; the SVG/PNG is produced later by the Python
``SVGRenderer`` / ``PNGRenderer``.
"""

from __future__ import annotations

import math
import re
from typing import List, Optional, Tuple

from app.models.visual_spec import (
    Arrow,
    Connection,
    Layout,
    Node,
    Section,
    Shape,
    TextElement,
    VisualSpecification,
)

# ── Colour palette (shared with the mock generator) ───────────────────────────

_PALETTE: List[str] = [
    "#2E86AB",
    "#A23B72",
    "#F18F01",
    "#C73E1D",
    "#10B981",
    "#6366F1",
]

_BG = "#0f172a"
_SECTION_BG = "#1e293b"
_SECTION_BORDER = "#334155"
_NODE_STROKE = "#1e293b"
_CONN_STROKE = "#64748b"
_TEXT_FOOTER = "#cbd5e1"
_TEXT_ANNOTATION = "#94a3b8"

# ── Layout helpers ────────────────────────────────────────────────────────────

_LAYOUT_W = 900
_LAYOUT_H = 650
_NODE_Y_BASE = 260


def _truncate(text: str, limit: int = 60) -> str:
    """Truncate *text* to *limit* chars, preserving whole words."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 3].rsplit(" ", 1)[0]
    return cut + "..."


def _derive_labels(prompt: str, count: int) -> List[str]:
    """Derive *count* node labels from *prompt*, padding with generics."""
    cleaned = re.sub(r"[.!?]+$", "", prompt.strip())
    parts = re.split(r"[,\;|\-]+|(?:\s+and\s+)|(?:\s+ or\s+)", cleaned)
    parts = [p.strip() for p in parts if p.strip()]

    # If the prompt is a single clause, try to extract from "about X"
    if len(parts) == 1 and "about" in parts[0].lower():
        after = parts[0].split("about", 1)[-1].strip()
        if after:
            parts = [after]

    labels = parts[:count]

    # Pad with generic component labels
    generics = ["Input", "Process", "Output", "Analysis", "Storage", "Display",
                "Control", "Monitoring", "Configuration", "Execution"]
    i = 0
    while len(labels) < count:
        labels.append(generics[i % len(generics)])
        i += 1

    return [labels[i] for i in range(count)]


def _node_count(complexity: str) -> int:
    """Map a complexity string to the number of nodes for medium-density layouts."""
    mapping = {"low": 2, "medium": 4, "high": 6}
    return mapping.get(complexity, mapping["medium"])


def _shape_count(complexity: str) -> int:
    """Number of decorative shapes per complexity."""
    mapping = {"low": 1, "medium": 3, "high": 5}
    return mapping.get(complexity, mapping["medium"])


def _text_count(complexity: str) -> int:
    """Number of annotation text elements (excluding footer) per complexity."""
    mapping = {"low": 0, "medium": 1, "high": 3}
    return mapping.get(complexity, mapping["medium"])


def _node_size(complexity: str) -> Tuple[float, float]:
    """(width, height) for nodes at a given complexity."""
    mapping = {"low": (180, 80), "medium": (160, 70), "high": (120, 60)}
    return mapping.get(complexity, mapping["medium"])


def _node_font_size(complexity: str) -> float:
    mapping = {"low": 14, "medium": 14, "high": 12}
    return mapping.get(complexity, mapping["medium"])


# ── Base spec builder ─────────────────────────────────────────────────────────

def _base_spec(
    prompt: str,
    complexity: str,
    title: Optional[str] = None,
) -> VisualSpecification:
    """Build a base VisualSpecification with a title section and footer text.

    Callers append nodes, shapes, connections, etc.
    """
    title_text = title or _truncate(prompt, 80) or "Visual Specification"
    desc = _truncate(prompt, 300)

    return VisualSpecification(
        title=title_text,
        layout=Layout(width=900, height=650, background=_BG, padding=40),
        title_font_size=32 if complexity == "high" else 36,
        title_fill="#ffffff",
        sections=[
            Section(
                title="Overview",
                x=40, y=40, width=820, height=140,
                fill=_SECTION_BG, stroke=_SECTION_BORDER, stroke_width=1,
                text_color="#e2e8f0",
                description=desc,
            )
        ],
        text=[
            TextElement(
                text=prompt,
                x=450, y=590,
                font_size=14 if complexity == "high" else 16,
                fill=_TEXT_FOOTER,
                align="center",  # type: ignore
            )
        ],
        shapes=[],
        arrows=[],
        nodes=[],
        connections=[],
    )


def _add_annotations(spec: VisualSpecification, prompt: str, complexity: str) -> None:
    """Append complexity-scaled annotation text elements."""
    n = _text_count(complexity)
    y_start = 555 if complexity == "high" else 560
    y_step = 15 if complexity == "high" else 20
    msgs: List[Tuple[str, float, str]] = [
        ("Key relationships between components", 12, _TEXT_ANNOTATION),
        ("Cross-component dependencies identified", 12, _TEXT_ANNOTATION),
        ("Data flow direction: left to right", 11, _TEXT_FOOTER),
    ]
    for i in range(n):
        msg, size, color = msgs[i % len(msgs)]
        spec.text.append(TextElement(
            text=msg, x=450, y=y_start - i * y_step,
            font_size=size, fill=color, align="center",  # type: ignore
        ))


def _add_decorative_shapes(
    spec: VisualSpecification,
    complexity: str,
    cx: float = 450,
    cy: float = 440,
) -> None:
    """Append complexity-scaled decorative shapes."""
    n = _shape_count(complexity)
    if n >= 1:
        spec.shapes.append(Shape(
            type="circle", cx=cx, cy=cy, r=50,
            fill=_PALETTE[3], stroke=_NODE_STROKE, stroke_width=2, opacity=0.2,
        ))
    if n >= 2:
        spec.shapes.append(Shape(
            type="rect", x=cx + 200, y=cy - 30, width=80, height=60,
            fill=_PALETTE[0], stroke=_NODE_STROKE, stroke_width=1, opacity=0.3,
        ))
    if n >= 3:
        spec.shapes.append(Shape(
            type="ellipse", cx=cx - 250, cy=cy, rx=30, ry=50,
            fill=_PALETTE[1], stroke=_NODE_STROKE, stroke_width=1, opacity=0.3,
        ))
    if n >= 4:
        spec.shapes.append(Shape(
            type="line", x1=40, y1=100, x2=860, y2=100,
            stroke=_CONN_STROKE, stroke_width=1, opacity=0.4,
        ))
    if n >= 5:
        spec.shapes.append(Shape(
            type="polygon",
            points=f"{cx},160 {cx+60},100 {cx+120},160 {cx+60},220",
            fill=_PALETTE[2], stroke=_NODE_STROKE, stroke_width=1, opacity=0.4,
        ))


def _make_nodes(
    labels: List[str],
    x_positions: List[float],
    y_pos: float,
    complexity: str,
) -> List[Node]:
    """Create Node objects with appropriate sizing and colors."""
    nw, nh = _node_size(complexity)
    fs = _node_font_size(complexity)
    nodes: List[Node] = []
    for i, (label, x) in enumerate(zip(labels, x_positions)):
        shape = "rounded_rect"
        if complexity == "high" and i % 2 == 0:
            shape = "circle"
        nodes.append(Node(
            id=f"n{i + 1}",
            label=_truncate(label, 18),
            x=x, y=y_pos,
            width=nw, height=nh,
            fill=_PALETTE[i % len(_PALETTE)],
            stroke=_NODE_STROKE,
            stroke_width=2,
            font_size=fs,
            shape=shape,
        ))
    return nodes


# ── Layout engine ─────────────────────────────────────────────────────────────


class LayoutEngine:
    """Generate reusable :class:`VisualSpecification` layouts.

    Each classmethod accepts a *prompt* and *complexity* and returns a
    fully-validated specification.
    """

    PROMPT = "prompt"
    COMPLEXITY = "complexity"

    # ── 1. Process Flow ─────────────────────────────────────────────────

    @classmethod
    def process_flow(cls, prompt: str, complexity: str = "medium") -> VisualSpecification:
        """Linear sequence of steps connected by arrows.

        Low: 2 steps · Medium: 4 steps · High: 6 steps (two-row layout).
        """
        spec = _base_spec(prompt, complexity, title="Process Flow")
        n = _node_count(complexity)
        labels = _derive_labels(prompt, n)
        nw, nh = _node_size(complexity)

        # Determine positions
        if n <= 4:
            spacing = (_LAYOUT_W - 120) / max(n, 2)
            xs = [120 + i * spacing for i in range(n)]
            ys = [_NODE_Y_BASE] * n
        else:
            # Two-row layout for 6 nodes
            spacing = 220
            xs = [130 + i * spacing for i in range(n)]
            ys = [_NODE_Y_BASE + (i // 3) * 120 for i in range(n)]

        nodes = _make_nodes(labels, xs, ys[0] if len(set(ys)) == 1 else ys[0], complexity)
        # Override with correct y positions per node
        for i, node in enumerate(nodes):
            node.y = ys[i]

        spec.nodes = nodes

        # Linear connections
        for i in range(n - 1):
            spec.connections.append(Connection(
                source=f"n{i + 1}", target=f"n{i + 2}",
                stroke=_CONN_STROKE, stroke_width=2 if complexity != "high" else 1,
            ))

        # Cross-connections for high complexity
        if complexity == "high" and n >= 4:
            for i in range(n - 3):
                spec.connections.append(Connection(
                    source=f"n{i + 1}", target=f"n{i + 4}",
                    stroke="#94a3b8", stroke_width=1,
                ))

        # Arrows
        if n >= 2:
            spec.arrows.append(Arrow(
                x1=nodes[0].x + nw + 10, y1=nodes[0].y + nh / 2,
                x2=nodes[1].x - 10, y2=nodes[1].y + nh / 2,
                stroke=_CONN_STROKE, stroke_width=2, marker=True,
            ))
        if n >= 3 and complexity in ("medium", "high"):
            spec.arrows.append(Arrow(
                x1=nodes[1].x + nw + 10, y1=nodes[1].y + nh / 2,
                x2=nodes[2].x - 10, y2=nodes[2].y + nh / 2,
                stroke=_CONN_STROKE, stroke_width=2, marker=True,
            ))

        _add_decorative_shapes(spec, complexity)
        _add_annotations(spec, prompt, complexity)
        return spec

    # ── 2. Timeline ─────────────────────────────────────────────────────

    @classmethod
    def timeline(cls, prompt: str, complexity: str = "medium") -> VisualSpecification:
        """Events on a horizontal timeline axis.

        Low: 2 events · Medium: 4 events · High: 6 events.
        """
        spec = _base_spec(prompt, complexity, title="Timeline")
        n = _node_count(complexity)
        labels = [f"Step {i + 1}" for i in range(n)]
        nw, nh = _node_size(complexity)

        timeline_y = _NODE_Y_BASE
        event_y = timeline_y - 30

        spacing = (_LAYOUT_W - 160) / max(n, 2)
        xs = [140 + i * spacing for i in range(n)]

        nodes = _make_nodes(labels, xs, event_y, complexity)
        # Adjust labels for timeline context
        prompt_labels = _derive_labels(prompt, n)
        for i, node in enumerate(nodes):
            if i < len(prompt_labels):
                node.label = _truncate(prompt_labels[i], 18)

        spec.nodes = nodes

        # Timeline line
        spec.shapes.append(Shape(
            type="line",
            x1=xs[0], y1=timeline_y, x2=xs[-1], y2=timeline_y,
            stroke=_CONN_STROKE, stroke_width=2, opacity=0.6,
        ))

        # Vertical connectors from events to timeline
        for i in range(n):
            spec.shapes.append(Shape(
                type="line",
                x1=xs[i] + nw / 2, y1=event_y + nh,
                x2=xs[i] + nw / 2, y2=timeline_y,
                stroke=_CONN_STROKE, stroke_width=1, opacity=0.4,
            ))

        # Time labels below
        for i in range(n):
            spec.text.append(TextElement(
                text=f"T{i}", x=xs[i] + nw / 2, y=timeline_y + 20,
                font_size=11, fill=_TEXT_ANNOTATION, align="center",  # type: ignore
            ))

        # Sequential connections
        for i in range(n - 1):
            spec.connections.append(Connection(
                source=f"n{i + 1}", target=f"n{i + 2}",
                stroke=_CONN_STROKE, stroke_width=2,
            ))

        _add_decorative_shapes(spec, complexity, cx=450, cy=timeline_y + 50)
        _add_annotations(spec, prompt, complexity)
        return spec

    # ── 3. Comparison ───────────────────────────────────────────────────

    @classmethod
    def comparison(cls, prompt: str, complexity: str = "medium") -> VisualSpecification:
        """Side-by-side comparison of two items.

        Low: 2 items/column · Medium: 3 items/column · High: 4 items/column.
        """
        spec = _base_spec(prompt, complexity, title="Comparison")
        items_per_col = {"low": 2, "medium": 3, "high": 4}.get(complexity, 3)
        nw, nh = _node_size(complexity)

        left_x = 130
        right_x = 500
        y_start = 240
        y_step = nh + 40

        labels = _derive_labels(prompt, items_per_col * 2)
        left_labels = labels[:items_per_col]
        right_labels = labels[items_per_col:items_per_col * 2]

        nodes: List[Node] = []
        for i, label in enumerate(left_labels):
            nodes.append(Node(
                id=f"n{i + 1}", label=_truncate(label, 18),
                x=left_x, y=y_start + i * y_step,
                width=nw, height=nh,
                fill=_PALETTE[0], stroke=_NODE_STROKE, stroke_width=2,
                font_size=_node_font_size(complexity), shape="rounded_rect",
            ))
        for i, label in enumerate(right_labels):
            nodes.append(Node(
                id=f"n{items_per_col + i + 1}", label=_truncate(label, 18),
                x=right_x, y=y_start + i * y_step,
                width=nw, height=nh,
                fill=_PALETTE[1], stroke=_NODE_STROKE, stroke_width=2,
                font_size=_node_font_size(complexity), shape="rounded_rect",
            ))

        spec.nodes = nodes

        # Column headers
        spec.text.append(TextElement(
            text="Left", x=left_x + nw / 2, y=y_start - 20,
            font_size=13, fill=_TEXT_FOOTER, weight="bold", align="center",  # type: ignore
        ))
        spec.text.append(TextElement(
            text="Right", x=right_x + nw / 2, y=y_start - 20,
            font_size=13, fill=_TEXT_FOOTER, weight="bold", align="center",  # type: ignore
        ))

        # Divider line
        total_h = y_start + (items_per_col - 1) * y_step
        spec.shapes.append(Shape(
            type="line",
            x1=450, y1=y_start - 20, x2=450, y2=total_h,
            stroke=_CONN_STROKE, stroke_width=2, opacity=0.5,
        ))

        _add_decorative_shapes(spec, complexity)
        _add_annotations(spec, prompt, complexity)
        return spec

    # ── 4. Hierarchy ─────────────────────────────────────────────────────

    @classmethod
    def hierarchy(cls, prompt: str, complexity: str = "medium") -> VisualSpecification:
        """Tree structure with parent-to-child connections.

        Low: 3-4 nodes (root + children) ·
        Medium: 5-6 nodes (root + 2 children + 2 grandchildren) ·
        High: 7-8 nodes (multi-level tree).
        """
        spec = _base_spec(prompt, complexity, title="Hierarchy")
        nw, nh = _node_size(complexity)

        if complexity == "low":
            # Root + 2 children
            root_x, root_y = 450, 220
            child_xs = [root_x - 150, root_x + 150]
            child_y = root_y + 100
            labels = _derive_labels(prompt, 3)
            positions = [(root_x, root_y)] + [(x, child_y) for x in child_xs]
            n = 3
        elif complexity == "medium":
            # Root + 2 children + 2 grandchildren each
            root_x, root_y = 450, 200
            child_y = root_y + 100
            grandchild_y = child_y + 100
            child_xs = [root_x - 150, root_x + 150]
            gc_xs = [
                [cx - 75, cx + 75] for cx in child_xs
            ]
            labels = _derive_labels(prompt, 7)[:7]
            positions = [(root_x, root_y)]
            for i, cx in enumerate(child_xs):
                positions.append((cx, child_y))
                for gc_x in gc_xs[i]:
                    positions.append((gc_x, grandchild_y))
            n = len(positions)
            labels = labels[:n]
        else:  # high
            # Root + 3 children + 2 grandchildren
            root_x, root_y = 450, 180
            child_y = root_y + 90
            grandchild_y = child_y + 90
            child_xs = [root_x - 200, root_x, root_x + 200]
            labels = _derive_labels(prompt, 7)[:7]
            positions = [(root_x, root_y)]
            for cx in child_xs:
                positions.append((cx, child_y))
                positions.append((cx - 75, grandchild_y))
                positions.append((cx + 75, grandchild_y))
            n = min(7, len(positions))
            positions = positions[:n]
            labels = labels[:n]

        nodes: List[Node] = []
        for i in range(n):
            x, y = positions[i]
            label = labels[i] if i < len(labels) else f"Node {i + 1}"
            fill_color = _PALETTE[0] if i == 0 else _PALETTE[(i + 2) % len(_PALETTE)]
            shape = "circle" if i == 0 else "rounded_rect"
            nodes.append(Node(
                id=f"n{i + 1}", label=_truncate(label, 18),
                x=x, y=y, width=nw, height=nh,
                fill=fill_color, stroke=_NODE_STROKE, stroke_width=2,
                font_size=_node_font_size(complexity), shape=shape,
            ))
        spec.nodes = nodes

        # Hierarchical connections: parent → child
        if complexity == "low":
            for i in range(1, 3):
                spec.connections.append(Connection(
                    source="n1", target=f"n{i + 1}",
                    stroke=_CONN_STROKE, stroke_width=2,
                ))
        elif complexity == "medium":
            # Root → children
            for i in [1, 2]:
                spec.connections.append(Connection(source="n1", target=f"n{i + 1}", stroke=_CONN_STROKE, stroke_width=2))
            # Children → grandchildren
            for child_idx, gc_start in [(1, 4), (2, 6)]:
                for j in range(2):
                    gc_idx = gc_start + j
                    if gc_idx <= n:
                        spec.connections.append(Connection(
                            source=f"n{child_idx + 1}", target=f"n{gc_idx}",
                            stroke=_CONN_STROKE, stroke_width=1,
                        ))
        else:  # high — same pattern
            for i in range(1, 4):
                spec.connections.append(Connection(source="n1", target=f"n{i + 1}", stroke=_CONN_STROKE, stroke_width=2))
            for child_idx in range(3):
                gc_base = 5 + child_idx * 2  # n5, n6 | n7, n8 | ...
                for j in range(2):
                    gc_idx = gc_base + j
                    if gc_idx <= n:
                        spec.connections.append(Connection(
                            source=f"n{child_idx + 2}", target=f"n{gc_idx}",
                            stroke=_CONN_STROKE, stroke_width=1,
                        ))

        _add_decorative_shapes(spec, complexity)
        _add_annotations(spec, prompt, complexity)
        return spec

    # ── 5. Cycle ─────────────────────────────────────────────────────────

    @classmethod
    def cycle(cls, prompt: str, complexity: str = "medium") -> VisualSpecification:
        """Nodes arranged in a circle with a cyclic flow.

        Low: 3 nodes · Medium: 5 nodes · High: 7 nodes.
        """
        spec = _base_spec(prompt, complexity, title="Cycle Diagram")
        n = {"low": 3, "medium": 5, "high": 7}.get(complexity, 5)
        labels = _derive_labels(prompt, n)
        nw, nh = _node_size(complexity)

        cx, cy, radius = 450, 350, 200

        nodes: List[Node] = []
        for i in range(n):
            angle = -math.pi / 2 + i * 2 * math.pi / n
            x = cx + radius * math.cos(angle) - nw / 2
            y = cy + radius * math.sin(angle) - nh / 2
            shape = "circle" if complexity == "high" and i % 2 == 0 else "rounded_rect"
            nodes.append(Node(
                id=f"n{i + 1}", label=_truncate(labels[i], 18),
                x=x, y=y, width=nw, height=nh,
                fill=_PALETTE[i % len(_PALETTE)], stroke=_NODE_STROKE, stroke_width=2,
                font_size=_node_font_size(complexity), shape=shape,
            ))
        spec.nodes = nodes

        # Cycle connections
        for i in range(n):
            spec.connections.append(Connection(
                source=f"n{i + 1}", target=f"n{(i % n) + 1}",
                stroke=_CONN_STROKE, stroke_width=2 if complexity != "high" else 1,
            ))

        # Central circle
        spec.shapes.append(Shape(
            type="circle", cx=cx, cy=cy, r=40,
            fill=_PALETTE[3], stroke=_NODE_STROKE, stroke_width=2, opacity=0.2,
        ))

        # Arrows between first two nodes
        if n >= 2:
            spec.arrows.append(Arrow(
                x1=nodes[0].x + nw + 10, y1=nodes[0].y + nh / 2,
                x2=nodes[1].x - 10, y2=nodes[1].y + nh / 2,
                stroke=_CONN_STROKE, stroke_width=2, marker=True,
            ))

        _add_annotations(spec, prompt, complexity)
        return spec

    # ── 6. Technical Diagram ─────────────────────────────────────────────

    @classmethod
    def technical_diagram(cls, prompt: str, complexity: str = "medium") -> VisualSpecification:
        """Detailed technical diagram with components and data flows.

        Low: 3 components · Medium: 5 components · High: 7 components
        with cross-connections and annotation layers.
        """
        spec = _base_spec(prompt, complexity, title="Technical Diagram")
        n = _node_count(complexity) + (1 if complexity == "high" else 0)
        n = min(n, 7)
        labels = _derive_labels(prompt, n)
        nw, nh = _node_size(complexity)

        # Grid layout
        cols = 3 if complexity == "high" else (3 if complexity == "medium" else 2)
        rows = math.ceil(n / cols)
        spacing_x = 220
        spacing_y = 110 if complexity == "high" else 120
        x_start = 120
        y_start = 220 if complexity == "high" else _NODE_Y_BASE

        nodes: List[Node] = []
        for i in range(n):
            row = i // cols
            col = i % cols
            x = x_start + col * spacing_x
            y = y_start + row * spacing_y
            node_shape = "rounded_rect" if (i % 2 == 0 or complexity == "low") else "circle"
            nodes.append(Node(
                id=f"n{i + 1}", label=_truncate(labels[i], 16),
                x=x, y=y, width=nw, height=nh,
                fill=_PALETTE[i % len(_PALETTE)], stroke=_NODE_STROKE, stroke_width=2,
                font_size=_node_font_size(complexity), shape=node_shape,
            ))
        spec.nodes = nodes

        # Dense connections
        for i in range(n - 1):
            spec.connections.append(Connection(
                source=f"n{i + 1}", target=f"n{i + 2}",
                stroke=_CONN_STROKE, stroke_width=1 if complexity == "high" else 2,
            ))

        if complexity == "high" and n >= 4:
            # Cross-connections
            for i in range(n - 3):
                spec.connections.append(Connection(
                    source=f"n{i + 1}", target=f"n{i + 4}",
                    stroke="#94a3b8", stroke_width=1,
                ))

        _add_decorative_shapes(spec, complexity)
        _add_annotations(spec, prompt, complexity)
        return spec

    # ── Dispatch ─────────────────────────────────────────────────────────

    @classmethod
    def generate(
        cls,
        prompt: str,
        layout: str = "process_flow",
        complexity: str = "medium",
    ) -> VisualSpecification:
        """Generate a spec using the named layout.

        Parameters
        ----------
        prompt:
            The user's natural-language prompt.
        layout:
            One of: ``process_flow``, ``timeline``, ``comparison``,
            ``hierarchy``, ``cycle``, ``technical_diagram``.
        complexity:
            ``low``, ``medium``, or ``high``.
        """
        layouts = {
            "process_flow": cls.process_flow,
            "timeline": cls.timeline,
            "comparison": cls.comparison,
            "hierarchy": cls.hierarchy,
            "cycle": cls.cycle,
            "technical_diagram": cls.technical_diagram,
        }
        if layout not in layouts:
            raise ValueError(
                f"Unknown layout '{layout}'. "
                f"Choose from: {', '.join(layouts)}"
            )
        return layouts[layout](prompt, complexity)

    @classmethod
    def available_layouts(cls) -> List[str]:
        """Return the list of available layout names."""
        return [
            "process_flow",
            "timeline",
            "comparison",
            "hierarchy",
            "cycle",
            "technical_diagram",
        ]


__all__ = ["LayoutEngine", "PNGRenderer"]
