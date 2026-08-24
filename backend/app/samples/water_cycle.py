"""
Sample visual specification: **The Water Cycle**.

This is a fully declarative, hand-authored infographic that exercises every
field of :class:`~app.models.visual_spec.VisualSpecification` — title, layout,
sections, text, shapes, arrows, nodes and connections — without involving any
AI model or paid service.

Expose it via the API with::

    GET /api/samples/water-cycle   → renders the SVG
    GET /api/samples/water-cycle/spec → returns the JSON specification
"""

from __future__ import annotations

from typing import Any, Dict

from app.models.visual_spec import VisualSpecification


def water_cycle_spec() -> Dict[str, Any]:
    """Return the Water Cycle specification as a plain JSON-serialisable dict."""
    return {
        "title": "The Water Cycle",
        "layout": {
            "width": 900,
            "height": 650,
            "background": "#0f172a",
            "padding": 40,
        },
        "title_font_size": 42,
        "title_fill": "#f8fafc",
        "sections": [
            {
                "title": "Overview",
                "x": 50,
                "y": 70,
                "width": 220,
                "height": 76,
                "fill": "rgba(15, 23, 42, 0.6)",
                "stroke": "#334159",
                "text_color": "#e2e8f0",
                "description": "Solar energy drives evaporation; water circulates endlessly.",
            },
            {
                "title": "Key Fact",
                "x": 630,
                "y": 70,
                "width": 220,
                "height": 76,
                "fill": "rgba(15, 23, 42, 0.6)",
                "stroke": "#334159",
                "text_color": "#e2e8f0",
                "description": "1.7 billion people rely on glaciers for water.",
            },
        ],
        # ── Sun (circle + rays) ──────────────────────────────────────────
        "shapes": [
            {
                "type": "circle", "cx": 80, "cy": 70, "r": 28,
                "fill": "#f59e0b", "stroke": "#d97706", "stroke_width": 2,
            },
            # Sun rays (plain lines, no arrowheads).
            {"type": "line", "x1": 80, "y1": 30, "x2": 80, "y2": 8,
             "stroke": "#f59e0b", "stroke_width": 2},
            {"type": "line", "x1": 80, "y1": 120, "x2": 80, "y2": 132,
             "stroke": "#f59e0b", "stroke_width": 2},
            {"type": "line", "x1": 38, "y1": 80, "x2": 26, "y2": 80,
             "stroke": "#f59e0b", "stroke_width": 2},
            {"type": "line", "x1": 122, "y1": 80, "x2": 134, "y2": 80,
             "stroke": "#f59e0b", "stroke_width": 2},
        ],
        # ── Raindrops falling from the precipitation node ───────────────
        "arrows": [
            {"x1": 450, "y1": 220, "x2": 450, "y2": 270,
             "stroke": "#38bdf8", "stroke_width": 3},
            {"x1": 430, "y1": 230, "x2": 420, "y2": 278,
             "stroke": "#38bdf8", "stroke_width": 3},
            {"x1": 470, "y1": 230, "x2": 480, "y2": 278,
             "stroke": "#38bdf8", "stroke_width": 3},
        ],
        # ── Cycle nodes ─────────────────────────────────────────────────
        "nodes": [
            {"id": "ocean", "label": "Ocean\n(Water Body)",
             "x": 360, "y": 500, "width": 180, "height": 70,
             "fill": "#0ea5e9", "stroke": "#0284c7", "font_size": 14},
            {"id": "evaporation", "label": "Evaporation\n(Water Vapor)",
             "x": 640, "y": 470, "width": 160, "height": 64,
             "fill": "#fef3c7", "stroke": "#d97706", "font_size": 13},
            {"id": "condensation", "label": "Condensation\n(Cloud Formation)",
             "x": 640, "y": 300, "width": 160, "height": 64,
             "fill": "#e2e8f0", "stroke": "#94a3b8", "font_size": 13},
            {"id": "precipitation", "label": "Precipitation\n(Rain / Snow)",
             "x": 360, "y": 200, "width": 180, "height": 70,
             "fill": "#a78bfa", "stroke": "#7c3aed", "font_size": 13},
            {"id": "runoff", "label": "Runoff\n(Rivers / Streams)",
             "x": 170, "y": 300, "width": 140, "height": 60,
             "fill": "#a7f3d0", "stroke": "#059669", "font_size": 13},
            {"id": "collection", "label": "Collection\n(Groundwater)",
             "x": 170, "y": 470, "width": 140, "height": 60,
             "fill": "#4ade80", "stroke": "#16a34a", "font_size": 13},
        ],
        # ── The cycle (directed flow) ───────────────────────────────────
        "connections": [
            {"source": "ocean", "target": "evaporation"},
            {"source": "evaporation", "target": "condensation"},
            {"source": "condensation", "target": "precipitation"},
            {"source": "precipitation", "target": "runoff"},
            {"source": "runoff", "target": "collection"},
            {"source": "collection", "target": "ocean"},
        ],
        # ── Supporting text labels ───────────────────────────────────────
        "text": [
            {"text": "Sun", "x": 80, "y": 108, "font_size": 12,
             "fill": "#fbbf24", "align": "center"},
            {"text": "Heat", "x": 80, "y": 40, "font_size": 11,
             "fill": "#fde68a", "align": "center"},
            {"text": "Warm moist air rises →", "x": 640, "y": 440,
             "font_size": 12, "fill": "#fef3c7", "align": "center"},
            {"text": "Forms clouds", "x": 720, "y": 270,
             "font_size": 12, "fill": "#e2e8f0", "align": "center"},
        ],
    }


def water_cycle() -> VisualSpecification:
    """Return a validated :class:`VisualSpecification` for the Water Cycle."""
    return VisualSpecification.model_validate(water_cycle_spec())
