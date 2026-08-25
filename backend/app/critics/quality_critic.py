"""
Visual quality critic — programmatic validation layer for generated visuals.

The :class:`VisualQualityCritic` inspects a
:class:`~app.models.visual_spec.VisualSpecification` (and optionally the SVG
document it produces) and returns a structured
:class:`~app.models.quality_report.QualityReport` containing:

* **issues**      — critical problems that make the visual invalid
  (out-of-bounds elements, broken connections, invalid SVG, empty content).
* **warnings**    — non-critical concerns (element overlap, spacing violations).
* **suggestions** — improvement recommendations (template mismatch, complexity
  mismatch).

The score starts at 100 and is penalised:

* −25 per issue
* −5  per warning
* −2  per suggestion

``passed`` is ``True`` iff there are zero issues.

No AI / LLM image-evaluation APIs are used.  All checks are deterministic.
"""

from __future__ import annotations

import math
import re
from typing import List, Optional, Tuple
from xml.etree import ElementTree as ET

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
    VisualSpecification,
)

# ── Constants ────────────────────────────────────────────────────────────────

# Minimum distance (px) between any two nodes before a warning is raised.
_MIN_NODE_SPACING = 30.0

# Minimum distance (px) between any two shapes before a warning is raised.
_MIN_SHAPE_SPACING = 20.0

# Overlap threshold: if two bounding boxes share more than this fraction of
# their area, it is considered an overlap.
_OVERLAP_AREA_THRESHOLD = 0.15

# Expected node-count ranges per complexity level (used for mismatch detection).
_COMPLEXITY_RANGES: dict[str, Tuple[int, int]] = {
    "low": (1, 4),
    "medium": (3, 7),
    "high": (5, 12),
}

# Expected shape-count ranges per complexity level.
_SHAPE_COMPLEXITY_RANGES: dict[str, Tuple[int, int]] = {
    "low": (0, 3),
    "medium": (2, 6),
    "high": (3, 10),
}

# Expected text-count ranges per complexity level.
_TEXT_COMPLEXITY_RANGES: dict[str, Tuple[int, int]] = {
    "low": (0, 3),
    "medium": (2, 6),
    "high": (3, 12),
}

# Title → template-name keyword map (mirrors TemplateEngine titles).
_TITLE_TO_TEMPLATE: List[Tuple[str, str]] = [
    ("Process Flow", "process_flow"),
    ("Timeline", "timeline"),
    ("Comparison", "comparison"),
    ("Cycle", "cycle"),
    ("Hierarchy", "hierarchy"),
    ("Data & Statistics", "statistics"),
    ("System Architecture", "technical_system"),
    ("Step-by-Step", "step_by_step"),
]


# ── Bounding-box helpers ─────────────────────────────────────────────────────


def _shape_bbox(shape: Shape) -> Optional[Tuple[float, float, float, float]]:
    """Return ``(x0, y0, x1, y1)`` bounding box for *shape*, or ``None`` if unknown."""
    t = shape.type
    if t in (ShapeType.RECT, ShapeType.ROUNDED_RECT):
        if shape.x is None or shape.y is None or shape.width is None or shape.height is None:
            return None
        return (shape.x, shape.y, shape.x + shape.width, shape.y + shape.height)
    if t == ShapeType.CIRCLE:
        if shape.cx is None or shape.cy is None or shape.r is None:
            return None
        r = shape.r
        return (shape.cx - r, shape.cy - r, shape.cx + r, shape.cy + r)
    if t == ShapeType.ELLIPSE:
        if shape.cx is None or shape.cy is None or shape.rx is None or shape.ry is None:
            return None
        return (shape.cx - shape.rx, shape.cy - shape.ry, shape.cx + shape.rx, shape.cy + shape.ry)
    if t == ShapeType.LINE:
        if None in (shape.x1, shape.y1, shape.x2, shape.y2):
            return None
        return (min(shape.x1, shape.x2), min(shape.y1, shape.y2),
                max(shape.x1, shape.x2), max(shape.y1, shape.y2))
    if t in (ShapeType.POLYLINE, ShapeType.POLYGON):
        if not shape.points:
            return None
        pts = _parse_points(shape.points)
        if not pts:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))
    return None


def _node_bbox(node: Node) -> Tuple[float, float, float, float]:
    """Return bounding box ``(x0, y0, x1, y1)`` for a node."""
    return (node.x, node.y, node.x + node.width, node.y + node.height)


def _text_bbox(text: TextElement) -> Tuple[float, float, float, float]:
    """Return an *estimated* bounding box for a text element.

    Uses a rough character-width estimate (0.6 × font_size) and a line-height
    of 1.2 × font_size.
    """
    char_w = 0.6 * text.font_size
    est_w = len(text.text) * char_w
    est_h = text.font_size * 1.2
    return (text.x - est_w / 2, text.y, text.x + est_w / 2, text.y + est_h)


def _arrow_bbox(arrow: Arrow) -> Tuple[float, float, float, float]:
    """Return bounding box for an arrow."""
    return (min(arrow.x1, arrow.x2), min(arrow.y1, arrow.y2),
            max(arrow.x1, arrow.x2), max(arrow.y1, arrow.y2))


def _parse_points(points_str: str) -> List[Tuple[float, float]]:
    """Parse an SVG ``points`` attribute string into ``(x, y)`` tuples."""
    coords = re.findall(r"-?\d+(?:\.\d+)?", points_str)
    return [(float(coords[i]), float(coords[i + 1])) for i in range(0, len(coords) - 1, 2)]


def _overlaps(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> bool:
    """Return ``True`` if rectangles *a* and *b* overlap (with area threshold)."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    inter_w = max(0, min(ax1, bx1) - max(ax0, bx0))
    inter_h = max(0, min(ay1, by1) - max(ay0, by0))
    if inter_w <= 0 or inter_h <= 0:
        return False
    inter_area = inter_w * inter_h
    area_a = max(0, (ax1 - ax0) * (ay1 - ay0))
    area_b = max(0, (bx1 - bx0) * (by1 - by0))
    min_area = min(area_a, area_b)
    return inter_area > min_area * _OVERLAP_AREA_THRESHOLD


def _distance(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    """Return the minimum centre-to-centre distance between two bboxes.

    If they overlap the distance is 0.
    """
    ax_cx = (a[0] + a[2]) / 2
    ay_cy = (a[1] + a[3]) / 2
    bx_cx = (b[0] + b[2]) / 2
    by_cy = (b[1] + b[3]) / 2
    return math.hypot(ax_cx - bx_cx, ay_cy - by_cy)


def _bbox_to_str(b: Tuple[float, float, float, float]) -> str:
    return f"({b[0]:.1f}, {b[1]:.1f})–({b[2]:.1f}, {b[3]:.1f})"


# ── Title → template resolution ──────────────────────────────────────────────


def _title_to_template(title: str) -> Optional[str]:
    """Best-effort mapping from a spec title to a template name."""
    tl = title.lower()
    for title_kw, template in _TITLE_TO_TEMPLATE:
        if title_kw.lower() in tl:
            return template
    return None


# ── The critic ───────────────────────────────────────────────────────────────


class VisualQualityCritic:
    """Programmatic quality validator for :class:`VisualSpecification`.

    Example::

        critic = VisualQualityCritic()
        report = critic.critique(spec, svg=svg_string, prompt="water cycle")
        if not report.passed:
            print(report.issues)
    """

    # ── Public API ────────────────────────────────────────────────────────

    def critique(
        self,
        spec: VisualSpecification,
        svg: Optional[str] = None,
        prompt: Optional[str] = None,
        expected_complexity: Optional[str] = None,
    ) -> QualityReport:
        """Run all available checks on *spec* (and optionally *svg*).

        Parameters
        ----------
        spec:
            The :class:`VisualSpecification` to evaluate.
        svg:
            Optional SVG document string produced by
            :class:`~app.renderers.svg_renderer.SVGRenderer`.  When provided,
            SVG-validity and SVG↔spec cross-checks are performed.
        prompt:
            The original user prompt.  When provided, template-mismatch
            detection is performed by comparing ``TemplateEngine.select_template``
            with the template implied by the spec's title.
        expected_complexity:
            The complexity level the caller *intended* (low / medium / high).
            When provided, the critic checks whether the spec's element counts
            fall within the expected range for that complexity.
        """
        report = QualityReport(passed=True, score=100.0)

        self._check_spec_validity(spec, report)
        self._check_empty_content(spec, report)
        self._check_out_of_bounds(spec, report)
        self._check_element_overlap(spec, report)
        self._check_min_spacing(spec, report)
        self._check_broken_connections(spec, report)
        self._check_arrows(spec, report)
        # SVG-specific checks (only if SVG is provided)
        if svg is not None:
            self._check_svg_validity(svg, report)
            self._check_svg_spec_consistency(svg, spec, report)
        # Prompt-aware checks
        if prompt is not None:
            self._check_template_mismatch(spec, prompt, report)
        # Complexity-aware checks
        if expected_complexity is not None:
            self._check_complexity_mismatch(spec, expected_complexity, report)
        else:
            self._check_complexity_denseness(spec, report)

        return report.finalize()

    # ── Individual checks ─────────────────────────────────────────────────

    # -- 1. Spec validity --

    def _check_spec_validity(self, spec: VisualSpecification, report: QualityReport) -> None:
        """Check that the spec object itself is internally consistent."""
        layout: Layout = spec.layout
        if layout.width <= 0 or layout.height <= 0:
            report.add_issue(f"Layout dimensions are non-positive: {layout.width}×{layout.height}")
        if layout.padding < 0:
            report.add_issue(f"Layout padding is negative: {layout.padding}")
        # Title must be non-empty (model validator already enforces this,
        # but double-check after model construction).
        if not spec.title or not spec.title.strip():
            report.add_issue("Spec title is empty or whitespace-only.")
        # Title font size
        if spec.title_font_size <= 0:
            report.add_issue("Title font size must be positive.")

    # -- 2. Missing / empty content --

    def _check_empty_content(self, spec: VisualSpecification, report: QualityReport) -> None:
        """Flag specs that have no visual content at all."""
        total_nodes = len(spec.nodes)
        total_shapes = len(spec.shapes)
        total_text = len(spec.text)
        total_arrows = len(spec.arrows)
        total_conns = len(spec.connections)

        if total_nodes == 0:
            report.add_issue("Specification has no nodes.")
        if total_shapes == 0:
            report.add_warning("Specification has no shapes (decorative or structural).")
        if total_text == 0:
            report.add_warning("Specification has no text elements.")
        if total_arrows == 0 and total_conns == 0:
            report.add_warning("Specification has no arrows or connections — visual may lack directionality.")

        # If everything is empty, add a comprehensive issue.
        if total_nodes == 0 and total_shapes == 0 and total_text == 0 and total_arrows == 0 and total_conns == 0:
            report.add_issue("Specification is completely empty — no visual content at all.")
            return

        # Check for empty/blank text in elements
        for i, txt in enumerate(spec.text):
            if not txt.text or not txt.text.strip():
                report.add_issue(f"Text element at index {i} has empty or whitespace-only content.")
        for i, sec in enumerate(spec.sections):
            if not sec.title or not sec.title.strip():
                report.add_issue(f"Section at index {i} has an empty title.")
        for i, node in enumerate(spec.nodes):
            if not node.label or not node.label.strip():
                report.add_issue(f"Node '{node.id}' (index {i}) has an empty label.")

    # -- 3. Out-of-bounds elements --

    def _check_out_of_bounds(self, spec: VisualSpecification, report: QualityReport) -> None:
        """Check that all visual elements are within canvas bounds."""
        layout = spec.layout
        # Use padding as the safe margin; elements beyond the canvas bounds
        # are critical issues, while elements within padding are warnings.
        cx0, cy0 = 0, 0
        cx1, cy1 = layout.width, layout.height
        padx, pady = layout.padding, layout.padding

        def _check_bbox(bbox: Tuple[float, float, float, float], label: str) -> None:
            x0, y0, x1, y1 = bbox
            if x0 < cx0 or y0 < cy0 or x1 > cx1 or y1 > cy1:
                report.add_issue(f"{label} is out of canvas bounds {bbox}. Canvas: 0×0→{layout.width}×{layout.height}")
            elif x0 < padx or y0 < pady or x1 > cx1 - padx or y1 > cy1 - pady:
                report.add_warning(f"{label} is near the canvas edge (outside padding): {_bbox_to_str(bbox)}")

        for i, shape in enumerate(spec.shapes):
            bbox = _shape_bbox(shape)
            if bbox is not None:
                _check_bbox(bbox, f"Shape {i} ({shape.type.value})")
        for i, node in enumerate(spec.nodes):
            bbox = _node_bbox(node)
            _check_bbox(bbox, f"Node '{node.id}'")
        for i, text in enumerate(spec.text):
            bbox = _text_bbox(text)
            _check_bbox(bbox, f"Text element {i}")
        for i, arrow in enumerate(spec.arrows):
            bbox = _arrow_bbox(arrow)
            _check_bbox(bbox, f"Arrow {i}")
        for i, sec in enumerate(spec.sections):
            bbox = (sec.x, sec.y, sec.x + sec.width, sec.y + sec.height)
            _check_bbox(bbox, f"Section '{sec.title}'")

    # -- 4. Element overlap --

    def _check_element_overlap(self, spec: VisualSpecification, report: QualityReport) -> None:
        """Detect overlapping nodes and shapes (warnings, not critical)."""
        # Node-node overlap
        node_bboxes = [(_node_bbox(n), f"n{i1}") for i1, n in enumerate(spec.nodes)]
        for i1 in range(len(node_bboxes)):
            for i2 in range(i1 + 1, len(node_bboxes)):
                b1, l1 = node_bboxes[i1]
                b2, l2 = node_bboxes[i2]
                if _overlaps(b1, b2):
                    report.add_warning(
                        f"Nodes overlap: {l1} {_bbox_to_str(b1)} and {l2} {_bbox_to_str(b2)}"
                    )

        # Shape-shape overlap (only for shapes with known bounding boxes)
        shape_bboxes: List[Tuple[Tuple[float, float, float, float], str]] = []
        for i, shape in enumerate(spec.shapes):
            bbox = _shape_bbox(shape)
            if bbox is not None:
                shape_bboxes.append((bbox, f"shape:{i}:{shape.type.value}"))
        for i1 in range(len(shape_bboxes)):
            for i2 in range(i1 + 1, len(shape_bboxes)):
                b1, l1 = shape_bboxes[i1]
                b2, l2 = shape_bboxes[i2]
                if _overlaps(b1, b2):
                    report.add_warning(
                        f"Shapes overlap: {l1} {_bbox_to_str(b1)} and {l2} {_bbox_to_str(b2)}"
                    )

        # Node-shape overlap (node inside a shape or vice versa)
        for nb, nl in node_bboxes:
            for sb, sl in shape_bboxes:
                if _overlaps(nb, sb):
                    report.add_warning(
                        f"Node {nl} overlaps with shape {sl}"
                    )

    # -- 5. Broken connections / arrows --

    def _check_broken_connections(
        self, spec: VisualSpecification, report: QualityReport
    ) -> None:
        """Check that every connection references an existing node id."""
        node_ids = {n.id for n in spec.nodes}
        for i, conn in enumerate(spec.connections):
            if conn.source not in node_ids:
                report.add_issue(
                    f"Connection {i} references missing source node: '{conn.source}'"
                )
            if conn.target not in node_ids:
                report.add_issue(
                    f"Connection {i} references missing target node: '{conn.target}'"
                )
            if conn.source == conn.target:
                report.add_warning(
                    f"Connection {i} is a self-loop: '{conn.source}' → '{conn.target}'"
                )

        # Check for duplicate connections
        seen: set[tuple[str, str]] = set()
        for i, conn in enumerate(spec.connections):
            key = (conn.source, conn.target)
            if key in seen:
                report.add_warning(f"Duplicate connection {i}: '{conn.source}' → '{conn.target}'")
            seen.add(key)

    def _check_arrows(self, spec: VisualSpecification, report: QualityReport) -> None:
        """Check arrows for zero-length and out-of-bounds issues."""
        layout = spec.layout
        for i, arrow in enumerate(spec.arrows):
            length = math.hypot(arrow.x2 - arrow.x1, arrow.y2 - arrow.y1)
            if length == 0:
                report.add_issue(f"Arrow {i} has zero length (same start and end point).")
            # Check bounds
            bbox = _arrow_bbox(arrow)
            x0, y0, x1, y1 = bbox
            if x0 < 0 or y0 < 0 or x1 > layout.width or y1 > layout.height:
                report.add_warning(f"Arrow {i} extends beyond canvas bounds: {_bbox_to_str(bbox)}")

    # -- 6. Minimum spacing / layout rules --

    def _check_min_spacing(self, spec: VisualSpecification, report: QualityReport) -> None:
        """Warn when nodes or shapes are too close together."""
        # Node spacing
        node_bboxes = [_node_bbox(n) for n in spec.nodes]
        for i1 in range(len(node_bboxes)):
            for i2 in range(i1 + 1, len(node_bboxes)):
                dist = _distance(node_bboxes[i1], node_bboxes[i2])
                # If they overlap, distance is 0 (already warned elsewhere).
                if dist > 0 and dist < _MIN_NODE_SPACING:
                    report.add_warning(
                        f"Nodes {i1} and {i2} are too close: centre distance {dist:.1f}px "
                        f"(minimum {_MIN_NODE_SPACING}px)"
                    )

        # Shape spacing (only between shapes that don't overlap)
        shape_bboxes: List[Tuple[float, float, float, float]] = []
        for shape in spec.shapes:
            bbox = _shape_bbox(shape)
            if bbox is not None:
                shape_bboxes.append(bbox)
        for i1 in range(len(shape_bboxes)):
            for i2 in range(i1 + 1, len(shape_bboxes)):
                dist = _distance(shape_bboxes[i1], shape_bboxes[i2])
                if dist > 0 and dist < _MIN_SHAPE_SPACING:
                    report.add_warning(
                        f"Shapes {i1} and {i2} are too close: centre distance {dist:.1f}px "
                        f"(minimum {_MIN_SHAPE_SPACING}px)"
                    )

    # -- 7. Complexity-level mismatch --

    def _check_complexity_mismatch(
        self, spec: VisualSpecification, expected: str, report: QualityReport
    ) -> None:
        """Check whether the spec's element counts match the expected complexity."""
        n_range = _COMPLEXITY_RANGES.get(expected)
        s_range = _SHAPE_COMPLEXITY_RANGES.get(expected)
        t_range = _TEXT_COMPLEXITY_RANGES.get(expected)

        n_nodes = len(spec.nodes)
        n_shapes = len(spec.shapes)
        n_text = len(spec.text)
        n_conns = len(spec.connections)

        if n_range is not None:
            if n_nodes < n_range[0] or n_nodes > n_range[1]:
                report.add_warning(
                    f"Node count {n_nodes} is outside the '{expected}' complexity range "
                    f"[{n_range[0]}, {n_range[1]}]."
                )
        if s_range is not None:
            if n_shapes < s_range[0] or n_shapes > s_range[1]:
                report.add_warning(
                    f"Shape count {n_shapes} is outside the '{expected}' complexity range "
                    f"[{s_range[0]}, {s_range[1]}]."
                )
        if t_range is not None:
            if n_text < t_range[0] or n_text > t_range[1]:
                report.add_warning(
                    f"Text count {n_text} is outside the '{expected}' complexity range "
                    f"[{t_range[0]}, {t_range[1]}]."
                )

        if n_conns == 0:
            report.add_suggestion(
                f"For '{expected}' complexity, consider adding connections to indicate relationships."
            )

    def _check_complexity_denseness(
        self, spec: VisualSpecification, report: QualityReport
    ) -> None:
        """Suggest a complexity adjustment based on the spec's density."""
        n_nodes = len(spec.nodes)
        n_shapes = len(spec.shapes)
        n_text = len(spec.text)

        # Determine inferred density
        total = n_nodes + n_shapes + n_text
        if total <= 5:
            report.add_suggestion("Spec is sparse — consider 'low' complexity for simpler visuals.")
        elif total >= 20:
            report.add_suggestion("Spec is dense — consider 'high' complexity for rich visuals.")

        # Check individual ranges for all complexities
        for complexity, (lo, hi) in _COMPLEXITY_RANGES.items():
            if lo <= n_nodes <= hi:
                match = complexity
                break
        else:
            match = None

        if match is None:
            report.add_suggestion(
                f"Node count {n_nodes} does not clearly fit any complexity tier (low 1–4, "
                f"medium 3–7, high 5–12). Consider adjusting."
            )

    # -- 8. Template mismatch --

    def _check_template_mismatch(
        self, spec: VisualSpecification, prompt: str, report: QualityReport
    ) -> None:
        """Check that the spec's template matches what the prompt implies."""
        try:
            from app.templates.engine import TemplateEngine
            expected = TemplateEngine.select_template(prompt)
        except Exception:
            expected = "process_flow"

        actual = _title_to_template(spec.title)
        if actual is None:
            report.add_suggestion(
                f"Could not determine template from spec title '{spec.title}'."
            )
        elif actual != expected:
            report.add_suggestion(
                f"Template mismatch: prompt implies '{expected}' but spec title "
                f"'{spec.title}' maps to '{actual}'."
            )

    # -- 9. SVG validity --

    def _check_svg_validity(self, svg: str, report: QualityReport) -> None:
        """Check that the SVG string is well-formed XML."""
        if not svg or not svg.strip():
            report.add_issue("SVG document is empty or whitespace-only.")
            return

        if not svg.strip().startswith("<svg"):
            report.add_issue("SVG document does not start with an <svg> tag.")
        if not svg.strip().endswith("</svg>"):
            report.add_issue("SVG document does not end with </svg>.")

        try:
            root = ET.fromstring(svg)
        except ET.ParseError as exc:
            report.add_issue(f"SVG is not well-formed XML: {exc}")
            return

        if root.tag and not root.tag.endswith("svg"):
            report.add_issue(f"SVG root element is not <svg>: {root.tag}")

    def _check_svg_spec_consistency(
        self, svg: str, spec: VisualSpecification, report: QualityReport
    ) -> None:
        """Cross-check that the SVG contains expected elements from the spec."""
        try:
            root = ET.fromstring(svg)
        except ET.ParseError:
            return  # already reported as an issue

        ns = "{http://www.w3.org/2000/svg}"
        all_tags = [el.tag for el in root.iter()]

        # Check title
        title_elems = root.findall(f"{ns}title")
        if title_elems:
            svg_title = (title_elems[0].text or "").strip()
            if svg_title != spec.title:
                report.add_warning(
                    f"SVG title '[{svg_title}]' does not match spec title '[{spec.title}]'."
                )

        # Check that node count is reflected (at least one text per node label)
        if spec.nodes:
            text_count = sum(1 for el in all_tags if el == f"{ns}text")
            if text_count < 1:
                report.add_warning("SVG has no text elements despite spec having nodes.")


__all__ = ["VisualQualityCritic"]
