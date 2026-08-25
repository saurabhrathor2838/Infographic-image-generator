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
from app.templates.engine import TemplateEngine

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

        Template selection is automatic: :meth:`TemplateEngine.select_template`
        analyses the prompt keywords and picks the most appropriate layout
        (``process_flow``, ``timeline``, ``comparison``, ``cycle``,
        ``hierarchy``, ``statistics``, ``technical_system``, or
        ``step_by_step``).  The selected template then generates a
        programmatically-validated :class:`VisualSpecification` whose density
        scales with *complexity*:

        * ``"low"``   → 2–3 nodes, 1–2 shapes, 1 arrow, 1–2 text elements.
        * ``"medium"`` → 3–4 nodes, 2–3 shapes, 2 arrows, 2 text elements.
        * ``"high"``  → 6+ nodes, 5+ shapes, dense connections, cross-links,
          and annotation text elements.
        """
        template = TemplateEngine.select_template(user_prompt)
        spec = TemplateEngine.generate(user_prompt, template, complexity)
        return spec.model_dump(mode="json")

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
