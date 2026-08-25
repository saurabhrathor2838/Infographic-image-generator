"""
Mock text generator for development and testing.

Produces a deterministic, rule-based :class:`~app.models.visual_spec.VisualSpecification`
JSON from the user's prompt **without** requiring any paid AI / LLM API calls.

This provider is activated by setting ``AI_PROVIDER=mock`` in the environment
(or ``.env``).  It allows the complete *frontend → backend → planner → SVG*
flow to be exercised locally and in tests while keeping the production code-path
(OpenAI) intact for when a real key is supplied.

The mock generator inspects the system prompt that
:class:`~app.agents.visual_planner.VisualPlannerAgent` builds (which embeds the
original user prompt and complexity level) and synthesises a valid visual
specification whose detail level scales with the requested complexity:

* **low**    — simple visual: 2–3 nodes, 1 shape, 1 arrow, 1 text element.
* **medium** — multiple components: 3–4 nodes, 2–3 shapes, 2 arrows, 2 text.
* **high**   — dense technical: 6–8 nodes, 4–6 shapes, dense connections,
  cross-connections, and annotation text elements.
"""

from __future__ import annotations

import json
import re
from typing import Any, List, Optional

from app.providers.base import ProviderConfig
from app.providers.text_generator import TextGenerator, TextResult

# A small palette of pleasant, schema-valid hex colours.
_PALETTE: List[str] = [
    "#2E86AB",
    "#A23B72",
    "#F18F01",
    "#C73E1D",
    "#10B981",
    "#6366F1",
]

# Generic node labels used when the prompt doesn't yield parseable keywords.
_DEFAULT_NODE_LABELS: List[str] = [
    "Key Point 1",
    "Key Point 2",
    "Key Point 3",
    "Key Point 4",
]

# Additional synthetic labels for high-complexity expansion.
_EXTRA_NODE_LABELS: List[str] = [
    "Component 5",
    "Component 6",
    "Component 7",
    "Component 8",
]


class MockTextGenerator(TextGenerator):
    """Deterministic LLM stand-in that always returns a valid spec JSON."""

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        super().__init__(config=config or ProviderConfig(name="mock"))

    # ── Public API ────────────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> TextResult:
        """Return a canned, valid ``VisualSpecification`` JSON string.

        The *system_prompt* (built by ``VisualPlannerAgent``) contains the
        original user request after the marker ``User prompt:`` as well as
        the requested complexity after ``Complexity:``.  We extract both
        so the generated title, description and detail level match the query.
        """
        user_prompt = self._extract_user_prompt(system_prompt) if system_prompt else "Infographic"
        complexity = self._extract_complexity(system_prompt) if system_prompt else "medium"
        spec = self._build_spec(user_prompt, complexity)
        return TextResult(text=json.dumps(spec), model="mock", usage={})

    async def health_check(self) -> bool:
        return True

    # ── Spec generation ───────────────────────────────────────────────────

    @staticmethod
    def _extract_user_prompt(system_prompt: str) -> str:
        """Pull the original user prompt out of the planner's system prompt."""
        match = re.search(r"User prompt:\s*(.*)", system_prompt, re.DOTALL)
        if match:
            return match.group(1).strip()
        return "Infographic"

    @staticmethod
    def _extract_complexity(system_prompt: str) -> str:
        """Pull the complexity level out of the planner's system prompt.

        The system prompt contains a line like::

            Visual type requested: infographic. Complexity: high.

        We extract the word after ``Complexity:`` (case-insensitive).
        """
        match = re.search(r"Complexity:\s*(\w+)", system_prompt, re.IGNORECASE)
        if match:
            complexity = match.group(1).lower()
            if complexity in ("low", "medium", "high"):
                return complexity
        return "medium"

    @staticmethod
    def _truncate(text: str, limit: int = 60) -> str:
        """Truncate *text* to *limit* characters, preserving whole words."""
        if len(text) <= limit:
            return text
        cut = text[: limit - 3].rsplit(" ", 1)[0]
        return cut + "..."

    def _build_spec(self, user_prompt: str, complexity: str = "medium") -> dict[str, Any]:
        """Build a valid :class:`VisualSpecification` dict from *user_prompt*.

        The *complexity* parameter controls the visual density:

        * ``"low"``   → 2–3 nodes, 1 shape, 1 arrow, 1 text element.
        * ``"medium"`` → 3–4 nodes, 2–3 shapes, 2 arrows, 2 text elements.
        * ``"high"``  → 6 nodes, 5 shapes, 3 arrows, dense connections,
          cross-connections, and annotation text elements.
        """
        title = self._truncate(user_prompt, 60) or "Infographic"
        node_labels = self._derive_node_labels(user_prompt)

        # ── Resolve labels & node count per complexity ────────────────────
        all_labels = list(node_labels)
        if complexity == "high":
            while len(all_labels) < 6:
                all_labels.append(_EXTRA_NODE_LABELS[len(all_labels) - len(node_labels)])
        if complexity == "low":
            num_nodes = min(2, len(all_labels))
        elif complexity == "high":
            num_nodes = min(6, len(all_labels))
        else:  # medium
            num_nodes = min(4, len(all_labels))

        # ── Layout geometry per complexity ────────────────────────────────
        if complexity == "low":
            spacing = 320
            node_w, node_h = 180, 80
            font_size = 14
            y_nodes = 320
            multi_row = False
        elif complexity == "high":
            spacing = 250
            node_w, node_h = 120, 60
            font_size = 12
            y_nodes = 230
            multi_row = True
            row_spacing = 120
        else:  # medium
            spacing = 200
            node_w, node_h = 160, 70
            font_size = 14
            y_nodes = 260
            multi_row = False

        # ── Nodes ─────────────────────────────────────────────────────────
        nodes: List[dict[str, Any]] = []
        for i in range(num_nodes):
            if multi_row and num_nodes > 4:
                row = i // 3
                col = i % 3
                x = 130 + col * spacing
                y = y_nodes + row * row_spacing
            else:
                x = 120 + i * spacing
                y = y_nodes

            label = all_labels[i]
            color = _PALETTE[i % len(_PALETTE)]

            # Alternate node shapes for visual variety at higher complexity.
            if complexity == "high" and i % 2 == 1:
                node_shape = "circle"
            else:
                node_shape = "rounded_rect"

            nodes.append(
                {
                    "id": f"n{i + 1}",
                    "label": self._truncate(label, 18),
                    "x": x,
                    "y": y,
                    "width": node_w,
                    "height": node_h,
                    "fill": color,
                    "stroke": "#1e293b",
                    "stroke_width": 2,
                    "font_size": font_size,
                    "shape": node_shape,
                }
            )

        # ── Connections (linear chain + optional cross-links) ─────────────
        connections: List[dict[str, Any]] = []
        if num_nodes > 1:
            for i in range(num_nodes - 1):
                connections.append(
                    {
                        "source": f"n{i + 1}",
                        "target": f"n{i + 2}",
                        "stroke": "#64748b",
                        "stroke_width": 2 if complexity != "high" else 1,
                    }
                )

        # High complexity: add cross-connections for a dense, technical look.
        if complexity == "high" and num_nodes >= 4:
            for i in range(num_nodes - 3):
                connections.append(
                    {
                        "source": f"n{i + 1}",
                        "target": f"n{i + 4}",
                        "stroke": "#94a3b8",
                        "stroke_width": 1,
                    }
                )

        # ── Shapes (decorative / structural elements) ────────────────────
        shapes: List[dict[str, Any]] = []
        if complexity == "low":
            shapes.append(
                {
                    "type": "circle",
                    "cx": 450,
                    "cy": 460,
                    "r": 40,
                    "fill": _PALETTE[3],
                    "stroke": "#1e293b",
                    "stroke_width": 2,
                    "opacity": 0.2,
                }
            )
        elif complexity == "high":
            shapes.extend(
                [
                    {
                        "type": "circle",
                        "cx": 450,
                        "cy": 440,
                        "r": 50,
                        "fill": _PALETTE[3],
                        "stroke": "#1e293b",
                        "stroke_width": 2,
                        "opacity": 0.15,
                    },
                    {
                        "type": "rect",
                        "x": 660,
                        "y": 370,
                        "width": 80,
                        "height": 60,
                        "fill": _PALETTE[0],
                        "stroke": "#1e293b",
                        "stroke_width": 1,
                        "opacity": 0.3,
                    },
                    {
                        "type": "ellipse",
                        "cx": 120,
                        "cy": 420,
                        "rx": 30,
                        "ry": 50,
                        "fill": _PALETTE[1],
                        "stroke": "#1e293b",
                        "stroke_width": 1,
                        "opacity": 0.3,
                    },
                    {
                        "type": "line",
                        "x1": 40,
                        "y1": 100,
                        "x2": 860,
                        "y2": 100,
                        "stroke": "#64748b",
                        "stroke_width": 1,
                        "opacity": 0.4,
                    },
                    {
                        "type": "polygon",
                        "points": "450,160 510,100 570,160 510,220",
                        "fill": _PALETTE[2],
                        "stroke": "#1e293b",
                        "stroke_width": 1,
                        "opacity": 0.4,
                    },
                ]
            )
        else:  # medium
            shapes.extend(
                [
                    {
                        "type": "circle",
                        "cx": 450,
                        "cy": 440,
                        "r": 50,
                        "fill": _PALETTE[3],
                        "stroke": "#1e293b",
                        "stroke_width": 2,
                        "opacity": 0.2,
                    },
                    {
                        "type": "rect",
                        "x": 650,
                        "y": 380,
                        "width": 80,
                        "height": 60,
                        "fill": _PALETTE[0],
                        "stroke": "#1e293b",
                        "stroke_width": 1,
                        "opacity": 0.3,
                    },
                    {
                        "type": "ellipse",
                        "cx": 200,
                        "cy": 440,
                        "rx": 30,
                        "ry": 50,
                        "fill": _PALETTE[1],
                        "stroke": "#1e293b",
                        "stroke_width": 1,
                        "opacity": 0.3,
                    },
                ]
            )

        # ── Arrows (free-standing directional indicators) ──────────────────
        arrows: List[dict[str, Any]] = []
        if len(nodes) >= 2:
            arrows.append(
                {
                    "x1": nodes[0]["x"] + node_w + 10,
                    "y1": nodes[0]["y"] + node_h / 2,
                    "x2": nodes[1]["x"] - 10,
                    "y2": nodes[1]["y"] + node_h / 2,
                    "stroke": "#64748b",
                    "stroke_width": 2,
                    "marker": True,
                }
            )
        if len(nodes) >= 3 and complexity in ("medium", "high"):
            arrows.append(
                {
                    "x1": nodes[1]["x"] + node_w + 10,
                    "y1": nodes[1]["y"] + node_h / 2,
                    "x2": nodes[2]["x"] - 10,
                    "y2": nodes[2]["y"] + node_h / 2,
                    "stroke": "#64748b",
                    "stroke_width": 2,
                    "marker": True,
                }
            )
        if len(nodes) >= 4 and complexity == "high":
            arrows.append(
                {
                    "x1": nodes[2]["x"] + node_w + 10,
                    "y1": nodes[2]["y"] + node_h / 2,
                    "x2": nodes[3]["x"] - 10,
                    "y2": nodes[3]["y"] + node_h / 2,
                    "stroke": "#64748b",
                    "stroke_width": 1,
                    "marker": True,
                }
            )

        # ── Text elements (footer + annotations) ──────────────────────────
        text_elements: List[dict[str, Any]] = [
            {
                "text": user_prompt,
                "x": 450,
                "y": 590,
                "font_size": 16,
                "fill": "#cbd5e1",
                "align": "center",
            }
        ]

        if complexity == "medium" and len(nodes) >= 3:
            text_elements.append(
                {
                    "text": "Key relationships between components",
                    "x": 450,
                    "y": 560,
                    "font_size": 13,
                    "fill": "#94a3b8",
                    "align": "center",
                }
            )

        if complexity == "high" and len(nodes) >= 4:
            text_elements.extend(
                [
                    {
                        "text": "Annotation: cross-component dependencies",
                        "x": 450,
                        "y": 530,
                        "font_size": 12,
                        "fill": "#94a3b8",
                        "align": "center",
                    },
                    {
                        "text": "Annotation: data flow direction",
                        "x": 450,
                        "y": 545,
                        "font_size": 12,
                        "fill": "#94a3b8",
                        "align": "center",
                    },
                    {
                        "text": "Note: all connections are directional",
                        "x": 450,
                        "y": 560,
                        "font_size": 11,
                        "fill": "#64748b",
                        "align": "center",
                    },
                    {
                        "text": "Layers: input → processing → output",
                        "x": 450,
                        "y": 575,
                        "font_size": 11,
                        "fill": "#64748b",
                        "align": "center",
                    },
                ]
            )

        # ── Assemble spec ────────────────────────────────────────────────
        spec: dict[str, Any] = {
            "title": title,
            "layout": {
                "width": 900,
                "height": 650,
                "background": "#0f172a",
                "padding": 40,
            },
            "title_font_size": 36 if complexity != "high" else 32,
            "title_fill": "#ffffff",
            "sections": [
                {
                    "title": "Overview",
                    "x": 40,
                    "y": 40,
                    "width": 820,
                    "height": 140,
                    "fill": "#1e293b",
                    "stroke": "#334155",
                    "stroke_width": 1,
                    "text_color": "#e2e8f0",
                    "description": self._truncate(user_prompt, 300),
                }
            ],
            "text": text_elements,
            "shapes": shapes,
            "arrows": arrows,
            "nodes": nodes,
            "connections": connections,
        }
        return spec

    @staticmethod
    def _derive_node_labels(user_prompt: str) -> List[str]:
        """Create a few meaningful node labels from the user prompt.

        Splits on common delimiters (``,` `;` `|` `-` `and` `or`) and falls
        back to a default list if nothing useful is found.
        """
        cleaned = re.sub(r"[.!?]+$", "", user_prompt.strip())
        parts = re.split(r"[,\;|\-]+|(?:\s+and\s+)|(?:\s+ or\s+)", cleaned)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 2:
            return parts[:4]
        # One-shot prompt like "Create an infographic about X"
        if len(parts) == 1 and "about" in parts[0].lower():
            after = parts[0].split("about", 1)[-1].strip()
            if after:
                return [after, "Supporting Details", "Takeaways"]
        return _DEFAULT_NODE_LABELS[:4]


__all__ = ["MockTextGenerator"]
