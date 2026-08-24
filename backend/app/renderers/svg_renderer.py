"""
SVG renderer for :class:`~app.models.visual_spec.VisualSpecification`.

Converts a validated visual specification into a self-contained SVG document
string.  The renderer is deliberately dependency-free (standard library only)
so it can run anywhere Python runs without extra packages.

Output is deterministic given the same input: elements are emitted in a
stable order (background → sections → shapes → arrows → connections → nodes
→ text → title) so the produced SVG is easy to test and diff.
"""

from __future__ import annotations

import html
from typing import List

from app.models.visual_spec import (
    TextAlign,
    Arrow,
    Connection,
    Layout,
    Node,
    Section,
    Shape,
    TextElement,
    VisualSpecification,
)


class SVGRenderer:
    """Render a :class:`VisualSpecification` as an SVG document string."""

    # IDs / constants reused across renders.
    _ARROWHEAD_ID = "arrowhead"
    _FONT_FAMILY = "Arial, Helvetica, sans-serif"

    # ── Public API ────────────────────────────────────────────────────────

    def render(self, spec: VisualSpecification) -> str:
        """Render *spec* to a complete SVG document string.

        Parameters
        ----------
        spec:
            A validated :class:`VisualSpecification`.

        Returns
        -------
        str
            A self-contained ``<svg>`` document.
        """
        layout: Layout = spec.layout
        width = _fmt(layout.width)
        height = _fmt(layout.height)

        parts: List[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" '
            f'font-family="{_escape_attr(self._FONT_FAMILY)}">',
            f"  <title>{_escape_text(spec.title)}</title>",
            self._defs(),
        ]

        # Background canvas.
        parts.append(
            f'  <rect x="0" y="0" width="{width}" height="{height}" '
            f'fill="{_escape_attr(layout.background)}" />'
        )

        # Title (top-centre, above the content grid).
        parts.append(self._render_title(spec))

        # Logical sections (titled containers).
        for section in spec.sections:
            parts.append(self._render_section(section))

        # Raw shape primitives (decoration / structure).
        for shape in spec.shapes:
            parts.append(self._render_shape(shape))

        # Free-standing directional arrows.
        for arrow in spec.arrows:
            parts.append(self._render_arrow(arrow))

        # Node-to-node connections (resolved to node centres).
        for conn in spec.connections:
            parts.append(self._render_connection(conn, spec.nodes))

        # Graph nodes (boxes/circles + labels).
        for node in spec.nodes:
            parts.append(self._render_node(node))

        # Free-standing text elements.
        for text in spec.text:
            parts.append(self._render_text(text))

        parts.append("</svg>")
        return "\n".join(parts)

    # ── Defs (arrowhead marker) ───────────────────────────────────────────

    def _defs(self) -> str:
        """Define reusable gradient / marker resources."""
        return (
            "  <defs>\n"
            f'    <marker id="{self._ARROWHEAD_ID}" '
            "markerWidth=\"10\" markerHeight=\"7\" refX=\"9\" refY=\"3.5\" "
            "orient=\"auto\" markerUnits=\"strokeWidth\">\n"
            "      <polygon points=\"0 0, 10 3.5, 0 7\" "
            "fill=\"context-stroke\" />\n"
            "    </marker>\n"
            "  </defs>"
        )

    # ── Title ─────────────────────────────────────────────────────────────

    def _render_title(self, spec: VisualSpecification) -> str:
        x = spec.layout.width / 2.0
        y = spec.layout.padding
        return (
            f'  <text x="{_fmt(x)}" y="{_fmt(y)}" '
            f'text-anchor="middle" font-size="{_fmt(spec.title_font_size)}" '
            f'fill="{_escape_attr(spec.title_fill)}" font-weight="700"'
            f' font-family="{_escape_attr(self._FONT_FAMILY)}">'
            f"{_escape_text(spec.title)}</text>"
        )

    # ── Sections ──────────────────────────────────────────────────────────

    def _render_section(self, section: Section) -> str:
        parts: List[str] = []
        parts.append(
            f'  <rect x="{_fmt(section.x)}" y="{_fmt(section.y)}" '
            f'width="{_fmt(section.width)}" height="{_fmt(section.height)}" '
            f'rx="8" ry="8" '
            f'fill="{_escape_attr(section.fill)}" '
            f'stroke="{_escape_attr(section.stroke)}" '
            f'stroke-width="{_fmt(section.stroke_width)}" />'
        )
        # Section title (left-aligned, just below the top edge).
        label_x = section.x + 12
        label_y = section.y + 20
        parts.append(
            f'  <text x="{_fmt(label_x)}" y="{_fmt(label_y)}" '
            f'text-anchor="start" font-size="14" font-weight="700" '
            f'fill="{_escape_attr(section.text_color)}" '
            f'font-family="{_escape_attr(self._FONT_FAMILY)}">'
            f"{_escape_text(section.title)}</text>"
        )
        if section.description:
            desc_x = section.x + 12
            desc_y = section.y + 40
            parts.append(
                f'  <text x="{_fmt(desc_x)}" y="{_fmt(desc_y)}" '
                f'text-anchor="start" font-size="12" '
                f'fill="{_escape_attr(section.text_color)}" '
                f'opacity="0.8" font-family="{_escape_attr(self._FONT_FAMILY)}">'
                f"{_escape_text(section.description)}</text>"
            )
        return "\n".join(parts)

    # ── Shapes ────────────────────────────────────────────────────────────

    def _render_shape(self, shape: Shape) -> str:
        t = shape.type.value
        if t == "rect":
            return (
                f'  <rect x="{_fmt(shape.x)}" y="{_fmt(shape.y)}" '
                f'width="{_fmt(shape.width)}" height="{_fmt(shape.height)}" '
                f'fill="{_escape_attr(shape.fill)}" '
                f'stroke="{_escape_attr(shape.stroke)}" '
                f'stroke-width="{_fmt(shape.stroke_width)}" '
                f'opacity="{_fmt(shape.opacity)}" />'
            )
        if t == "rounded_rect":
            rx = shape.rx if shape.rx is not None else (shape.width or 12)
            ry = shape.ry if shape.ry is not None else (shape.height or 12)
            return (
                f'  <rect x="{_fmt(shape.x)}" y="{_fmt(shape.y)}" '
                f'width="{_fmt(shape.width)}" height="{_fmt(shape.height)}" '
                f'rx="{_fmt(rx)}" ry="{_fmt(ry)}" '
                f'fill="{_escape_attr(shape.fill)}" '
                f'stroke="{_escape_attr(shape.stroke)}" '
                f'stroke-width="{_fmt(shape.stroke_width)}" '
                f'opacity="{_fmt(shape.opacity)}" />'
            )
        if t == "circle":
            return (
                f'  <circle cx="{_fmt(shape.cx)}" cy="{_fmt(shape.cy)}" '
                f'r="{_fmt(shape.r)}" '
                f'fill="{_escape_attr(shape.fill)}" '
                f'stroke="{_escape_attr(shape.stroke)}" '
                f'stroke-width="{_fmt(shape.stroke_width)}" '
                f'opacity="{_fmt(shape.opacity)}" />'
            )
        if t == "ellipse":
            return (
                f'  <ellipse cx="{_fmt(shape.cx)}" cy="{_fmt(shape.cy)}" '
                f'rx="{_fmt(shape.rx)}" ry="{_fmt(shape.ry)}" '
                f'fill="{_escape_attr(shape.fill)}" '
                f'stroke="{_escape_attr(shape.stroke)}" '
                f'stroke-width="{_fmt(shape.stroke_width)}" '
                f'opacity="{_fmt(shape.opacity)}" />'
            )
        if t == "line":
            return self._render_arrow_like(
                shape.x1, shape.y1, shape.x2, shape.y2,
                shape.stroke, shape.stroke_width, shape.opacity,
                marker=False,
            )
        if t in ("polyline", "polygon"):
            tag = "polyline" if t == "polyline" else "polygon"
            return (
                f'  <{tag} points="{_escape_attr(shape.points)}" '
                f'fill="{_escape_attr(shape.fill)}" '
                f'stroke="{_escape_attr(shape.stroke)}" '
                f'stroke-width="{_fmt(shape.stroke_width)}" '
                f'opacity="{_fmt(shape.opacity)}" />'
            )
        raise ValueError(f"unsupported shape type: {t!r}")

    # ── Arrows / lines ─────────────────────────────────────────────────────

    def _render_arrow(self, arrow: Arrow) -> str:
        return self._render_arrow_like(
            arrow.x1, arrow.y1, arrow.x2, arrow.y2,
            arrow.stroke, arrow.stroke_width, 1.0,
            marker=arrow.marker,
        )

    def _render_arrow_like(
        self,
        x1, y1, x2, y2,
        stroke: str, stroke_width: float,
        opacity: float, marker: bool,
    ) -> str:
        marker_end = (
            f' marker-end="url(#{self._ARROWHEAD_ID})"' if marker else ""
        )
        return (
            f'  <line x1="{_fmt(x1)}" y1="{_fmt(y1)}" '
            f'x2="{_fmt(x2)}" y2="{_fmt(y2)}" '
            f'stroke="{_escape_attr(stroke)}" '
            f'stroke-width="{_fmt(stroke_width)}"{marker_end} '
            f'opacity="{_fmt(opacity)}" />'
        )

    # ── Connections (node-to-node) ──────────────────────────────────────────

    def _render_connection(self, conn: Connection, nodes: List[Node]) -> str:
        source = _find_node(nodes, conn.source)
        target = _find_node(nodes, conn.target)
        if source is None or target is None:
            # Validation usually prevents this; skip gracefully if not.
            return ""
        sx, sy, tx, ty = _edge_points(source, target)
        return self._render_arrow_like(
            sx, sy, tx, ty,
            conn.stroke, conn.stroke_width, 1.0,
            marker=True,
        )

    # ── Nodes ─────────────────────────────────────────────────────────────

    def _render_node(self, node: Node) -> str:
        parts: List[str] = []
        if node.shape == "circle":
            cx = node.x + node.width / 2.0
            cy = node.y + node.height / 2.0
            r = min(node.width, node.height) / 2.0
            parts.append(
                f'  <circle cx="{_fmt(cx)}" cy="{_fmt(cy)}" r="{_fmt(r)}" '
                f'fill="{_escape_attr(node.fill)}" '
                f'stroke="{_escape_attr(node.stroke)}" '
                f'stroke-width="{_fmt(node.stroke_width)}" />'
            )
            # Label centred on the circle.
            parts.append(self._text_element(
                cx, cy, node.label, "middle", "middle",
                node.font_size, node.stroke, "700",
            ))
            return "\n".join(parts)

        # Default: rounded rect node.
        rx = 10
        parts.append(
            f'  <rect x="{_fmt(node.x)}" y="{_fmt(node.y)}" '
            f'width="{_fmt(node.width)}" height="{_fmt(node.height)}" '
            f'rx="{rx}" ry="{rx}" '
            f'fill="{_escape_attr(node.fill)}" '
            f'stroke="{_escape_attr(node.stroke)}" '
            f'stroke-width="{_fmt(node.stroke_width)}" />'
        )
        # Label centred in the box.
        cx = node.x + node.width / 2.0
        cy = node.y + node.height / 2.0
        parts.append(self._text_element(
            cx, cy, node.label, "middle", "middle",
            node.font_size, node.stroke, "700",
        ))
        return "\n".join(parts)

    # ── Free text ─────────────────────────────────────────────────────────

    def _render_text(self, text: TextElement) -> str:
        anchor = {
            TextAlign.LEFT: "start",
            TextAlign.CENTER: "middle",
            TextAlign.RIGHT: "end",
        }.get(text.align, "start")
        return self._text_element(
            text.x, text.y, text.text, anchor, "hanging",
            text.font_size, text.fill, "normal" if text.weight == "normal" else text.weight,
        )

    def _text_element(
        self,
        x: float, y: float, content: str,
        anchor: str, dominant_baseline: str,
        font_size: float, fill: str, weight: str,
    ) -> str:
        return (
            f'  <text x="{_fmt(x)}" y="{_fmt(y)}" '
            f'text-anchor="{anchor}" dominant-baseline="{dominant_baseline}" '
            f'font-size="{_fmt(font_size)}" fill="{_escape_attr(fill)}" '
            f'font-weight="{weight}" font-family="{_escape_attr(self._FONT_FAMILY)}">'
            f"{_escape_text(content)}</text>"
        )

    # ── Helpers ───────────────────────────────────────────────────────────


def _fmt(value: float) -> str:
    """Format a number for SVG output, trimming needless precision."""
    if value is None:
        return "0"
    if isinstance(value, (int, float)):
        # Drop trailing zeros for cleaner SVG, keep reasonable precision.
        s = f"{value:.4f}".rstrip("0").rstrip(".")
        return s if s else "0"
    return str(value)


def _escape_attr(value: str) -> str:
    """Escape a string for use inside a double-quoted SVG attribute."""
    if value is None:
        return ""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _escape_text(value: str) -> str:
    """Escape text content for SVG."""
    if value is None:
        return ""
    return html.escape(str(value), quote=False)


def _find_node(nodes: List[Node], node_id: str) -> Node | None:
    for node in nodes:
        if node.id == node_id:
            return node
    return None


def _edge_points(source: Node, target: Node) -> tuple:
    """Return (source_edge_x, source_edge_y, target_edge_x, target_edge_y)
    so that a connection line joins the edges of two node bounding boxes
    rather than their centres."""
    sx = source.x + source.width / 2.0
    sy = source.y + source.height / 2.0
    tx = target.x + target.width / 2.0
    ty = target.y + target.height / 2.0
    dx = tx - sx
    dy = ty - sy
    dist = (dx * dx + dy * dy) ** 0.5
    if dist == 0:
        return sx, sy, tx, ty
    ux = dx / dist
    uy = dy / dist
    # Approximate each node by a radius derived from its bounding box.
    r1 = min(source.width, source.height) / 2.0
    r2 = min(target.width, target.height) / 2.0
    return (
        sx + ux * r1,
        sy + uy * r1,
        tx - ux * r2,
        ty - uy * r2,
    )
