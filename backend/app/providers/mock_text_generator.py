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
original user prompt) and synthesises a small but valid infographic spec with
title, layout, sections, nodes and connections.
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
        original user request after the marker ``User prompt:``.  We extract
        it so the generated title and description are relevant to the query.
        """
        user_prompt = self._extract_user_prompt(system_prompt) if system_prompt else "Infographic"
        spec = self._build_spec(user_prompt)
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
    def _truncate(text: str, limit: int = 60) -> str:
        """Truncate *text* to *limit* characters, preserving whole words."""
        if len(text) <= limit:
            return text
        cut = text[: limit - 3].rsplit(" ", 1)[0]
        return cut + "..."

    def _build_spec(self, user_prompt: str) -> dict[str, Any]:
        """Build a valid :class:`VisualSpecification` dict from *user_prompt*."""
        title = self._truncate(user_prompt, 60) or "Infographic"

        # Derive 3-4 node labels by splitting the prompt into clauses.
        node_labels = self._derive_node_labels(user_prompt)

        nodes: List[dict[str, Any]] = []
        connections: List[dict[str, Any]] = []
        cx_start = 120
        node_w = 160
        node_h = 70
        spacing = 200
        for i, label in enumerate(node_labels):
            x = cx_start + i * spacing
            y = 260
            color = _PALETTE[i % len(_PALETTE)]
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
                    "font_size": 14,
                    "shape": "rounded_rect",
                }
            )
            if i > 0:
                connections.append(
                    {
                        "source": f"n{i}",
                        "target": f"n{i + 1}",
                        "stroke": "#64748b",
                        "stroke_width": 2,
                    }
                )

        # If we only got one node, still add an arrow for visual interest.
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

        spec: dict[str, Any] = {
            "title": title,
            "layout": {
                "width": 900,
                "height": 650,
                "background": "#0f172a",
                "padding": 40,
            },
            "title_font_size": 36,
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
            "text": [
                {
                    "text": user_prompt,
                    "x": 450,
                    "y": 580,
                    "font_size": 16,
                    "fill": "#cbd5e1",
                    "align": "center",
                }
            ],
            "shapes": [
                {
                    "type": "circle",
                    "cx": 450,
                    "cy": 440,
                    "r": 50,
                    "fill": _PALETTE[3],
                    "stroke": "#1e293b",
                    "stroke_width": 2,
                    "opacity": 0.2,
                }
            ],
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
        parts = re.split(r"[,\;|\-]+|(?:\s+and\s+)|(?:\s+or\s+)", cleaned)
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
