"""
Automatic Visual Revision Engine.

Wraps :class:`~app.critics.quality_critic.VisualQualityCritic` in an iterative
loop that attempts to correct a :class:`~app.models.visual_spec.VisualSpecification`
when the critic finds issues:

    Generate → Critic → ✅ PASS → Final
                          → ❌ FAIL → Revise → Critic → ✅ PASS → Final
                                        → ❌ FAIL → Revise → … (max 3)

**Revision strategies (by attempt):**

* **Attempt 0 — structural fixes:** clamp out-of-bounds nodes, remove
  broken/dangling/self-loop/duplicate connections, remove zero-length
  arrows, spread overlapping nodes, fix minimum-node-spacing.
* **Attempt 1 — template regeneration:** re-generate the spec from the
  correct template at the expected complexity (requires ``prompt``).
* **Attempt 2 — simplification:** re-generate at *low* complexity to
  produce a minimal, valid spec (requires ``prompt``).

If no ``prompt`` is supplied, only structural fixes are attempted.

The engine never modifies the caller's original spec (it works on a deep
copy).  Image generation is 100 % Python (SVGRenderer + PNGRenderer) — no
AI image-generation APIs are used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.critics.quality_critic import _node_bbox, _overlaps, _distance
from app.critics.quality_critic import VisualQualityCritic
from app.models.quality_report import QualityReport
from app.models.visual_spec import (
    Arrow,
    Connection,
    Node,
    Section,
    Shape,
    VisualSpecification,
)
from app.renderers.png_renderer import PNGRenderer
from app.renderers.svg_renderer import SVGRenderer
from app.templates.engine import TemplateEngine

# ── Defaults ──────────────────────────────────────────────────────────────────

_MIN_NODE_SPACING = 30.0


# ── Result container ───────────────────────────────────────────────────────────


@dataclass
class RevisionResult:
    """Outcome of the revision loop.

    Attributes
    ----------
    spec :
        The final (possibly revised) :class:`VisualSpecification`.
    svg :
        SVG document string rendered from the final spec.
    png :
        PNG bytes rendered from the final spec, or ``None`` if
        ``render_png`` was ``False``.
    report :
        Final :class:`QualityReport` produced by the critic (includes SVG
        checks).
    revisions :
        Number of revision attempts made (0 = passed on first critique).
    passed :
        ``True`` if the final report has zero issues.
    """

    spec: VisualSpecification
    svg: str
    png: Optional[bytes]
    report: QualityReport
    revisions: int
    passed: bool


# ── The engine ─────────────────────────────────────────────────────────────────


class RevisionEngine:
    """Iterative specification revision loop.

    Example::

        engine = RevisionEngine()
        result = engine.revise(
            spec, prompt="water cycle", complexity="high"
        )
        print(result.revisions, result.passed, result.report.score)
    """

    MAX_REVISIONS = 3

    def __init__(
        self,
        critic: Optional[VisualQualityCritic] = None,
        svg_renderer: Optional[SVGRenderer] = None,
        png_renderer: Optional[PNGRenderer] = None,
    ) -> None:
        self._critic: VisualQualityCritic = critic or VisualQualityCritic()
        self._svg_renderer: SVGRenderer = svg_renderer or SVGRenderer()
        self._png_renderer: PNGRenderer = png_renderer or PNGRenderer()

    # ── Public API ────────────────────────────────────────────────────────

    def revise(
        self,
        spec: VisualSpecification,
        *,
        prompt: Optional[str] = None,
        complexity: Optional[str] = None,
        render_png: bool = True,
    ) -> RevisionResult:
        """Run the full revise → critique loop.

        Parameters
        ----------
        spec :
            The initial (possibly flawed) specification.
        prompt :
            Original user prompt.  When provided, the engine can regenerate
            the spec via :class:`TemplateEngine` if structural fixes are
            insufficient.
        complexity :
            Expected complexity level (sent to the critic for mismatch
            detection).
        render_png :
            Whether to render PNG output in addition to SVG.
        """
        # Deep-copy so the caller's spec is never mutated.
        current: VisualSpecification = spec.model_copy(deep=True)
        revisions = 0

        # Initial critique (spec-level only, no SVG yet).
        report = self._critic.critique(
            current, prompt=prompt, expected_complexity=complexity
        )

        # Revision loop: at most MAX_REVISIONS attempts.
        for attempt in range(self.MAX_REVISIONS):
            if report.passed:
                break

            current = self._apply_revision(current, report, attempt, prompt, complexity)
            revisions += 1

            report = self._critic.critique(
                current, prompt=prompt, expected_complexity=complexity
            )

        # Render final image.
        svg = self._svg_renderer.render(current)
        png_bytes: Optional[bytes] = self._png_renderer.render(current) if render_png else None

        # Final critique including SVG checks.
        final_report = self._critic.critique(
            current, svg=svg, prompt=prompt, expected_complexity=complexity
        )

        return RevisionResult(
            spec=current,
            svg=svg,
            png=png_bytes,
            report=final_report,
            revisions=revisions,
            passed=final_report.passed,
        )

    # ── Revision strategies ───────────────────────────────────────────────

    def _apply_revision(
        self,
        spec: VisualSpecification,
        report: QualityReport,
        attempt: int,
        prompt: Optional[str],
        complexity: Optional[str],
    ) -> VisualSpecification:
        """Choose and apply a revision strategy based on the attempt number."""
        if attempt == 0:
            # Strategy 1: structural fixes (geometry + connection cleanup).
            return self._structural_revisions(spec)
        elif attempt == 1 and prompt is not None:
            # Strategy 2: regenerate from the correct template at expected complexity.
            template = TemplateEngine.select_template(prompt)
            return TemplateEngine.generate(prompt, template, complexity or "medium")
        elif attempt == 2 and prompt is not None:
            # Strategy 3: regenerate at low complexity (simplest valid spec).
            template = TemplateEngine.select_template(prompt)
            return TemplateEngine.generate(prompt, template, "low")
        else:
            # No prompt available — keep trying structural fixes.
            return self._structural_revisions(spec)

    # ── Structural revision helpers ───────────────────────────────────────

    def _structural_revisions(self, spec: VisualSpecification) -> VisualSpecification:
        """Apply all structural fixes to a copy of *spec*."""
        spec = spec.model_copy(deep=True)
        self._fix_out_of_bounds(spec)
        self._fix_broken_connections(spec)
        self._fix_zero_length_arrows(spec)
        self._fix_overlaps(spec)
        self._fix_spacing(spec)
        return spec

    def _fix_out_of_bounds(self, spec: VisualSpecification) -> None:
        """Clamp nodes within the canvas content area (inside padding)."""
        layout = spec.layout
        padx = layout.padding
        pady = layout.padding
        for node in spec.nodes:
            # Clamp left / top
            if node.x < padx:
                node.x = padx
            if node.y < pady:
                node.y = pady
            # Clamp right / bottom
            right = node.x + node.width
            bottom = node.y + node.height
            if right > layout.width - padx:
                node.x = max(padx, layout.width - padx - node.width)
            if bottom > layout.height - pady:
                node.y = max(pady, layout.height - pady - node.height)

    def _fix_broken_connections(self, spec: VisualSpecification) -> None:
        """Remove connections referencing non-existent nodes, self-loops, duplicates."""
        node_ids = {n.id for n in spec.nodes}
        seen: set = set()
        kept: List[Connection] = []
        for conn in spec.connections:
            if conn.source not in node_ids or conn.target not in node_ids:
                continue
            if conn.source == conn.target:
                continue
            key = (conn.source, conn.target)
            if key in seen:
                continue
            seen.add(key)
            kept.append(conn)
        spec.connections = kept

    def _fix_zero_length_arrows(self, spec: VisualSpecification) -> None:
        """Remove arrows where start and end points are identical."""
        kept: List[Arrow] = []
        for arrow in spec.arrows:
            length = math.hypot(arrow.x2 - arrow.x1, arrow.y2 - arrow.y1)
            if length > 0:
                kept.append(arrow)
        spec.arrows = kept

    def _fix_overlaps(self, spec: VisualSpecification) -> None:
        """Spread overlapping nodes horizontally to remove overlap."""
        layout = spec.layout
        if len(spec.nodes) < 2:
            return
        node_bboxes: List[Tuple[Tuple[float, float, float, float], int]] = [
            (_node_bbox(n), i) for i, n in enumerate(spec.nodes)
        ]
        for i1 in range(len(node_bboxes)):
            for i2 in range(i1 + 1, len(node_bboxes)):
                b1, idx1 = node_bboxes[i1]
                b2, idx2 = node_bboxes[i2]
                if _overlaps(b1, b2):
                    n2 = spec.nodes[idx2]
                    overlap_x = min(b1[2], b2[2]) - max(b1[0], b2[0])
                    n2.x = min(n2.x + overlap_x + 10, layout.width - layout.padding - n2.width)
        # Re-clamp any nodes pushed out of bounds.
        self._fix_out_of_bounds(spec)

    def _fix_spacing(self, spec: VisualSpecification) -> None:
        """Ensure minimum centre-to-centre spacing between nodes."""
        if len(spec.nodes) < 2:
            return
        node_bboxes = [_node_bbox(n) for n in spec.nodes]
        for i1 in range(len(node_bboxes)):
            for i2 in range(i1 + 1, len(node_bboxes)):
                b1 = node_bboxes[i1]
                b2 = node_bboxes[i2]
                dist = _distance(b1, b2)
                if 0 < dist < _MIN_NODE_SPACING:
                    a = spec.nodes[i1]
                    b = spec.nodes[i2]
                    ax_cx = a.x + a.width / 2
                    ay_cy = a.y + a.height / 2
                    bx_cx = b.x + b.width / 2
                    by_cy = b.y + b.height / 2
                    dx = bx_cx - ax_cx
                    dy = by_cy - ay_cy
                    if dx == 0 and dy == 0:
                        dx, dy = 1.0, 0.0
                    length = math.hypot(dx, dy)
                    ux = dx / length
                    uy = dy / length
                    push = (_MIN_NODE_SPACING - dist) / 2 + 5
                    a.x -= ux * push
                    a.y -= uy * push
                    b.x += ux * push
                    b.y += uy * push
        # Re-clamp after moving.
        self._fix_out_of_bounds(spec)


__all__ = ["RevisionEngine", "RevisionResult"]
