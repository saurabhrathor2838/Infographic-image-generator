"""
AI Planner Agent.

Converts a natural-language user prompt into a validated
:class:`~app.models.visual_spec.VisualSpecification` by calling a configured
LLM (text generator) and parsing its JSON output.

Workflow
--------
1. Build a system prompt describing the ``VisualSpecification`` schema.
2. Call the LLM (``self._text_generator``) for up to ``max_retries`` attempts.
3. Parse the raw text — tolerating surrounding prose and markdown fences.
4. Validate with the Pydantic schema (this is the safety net: *any* invalid
   output is rejected before it ever reaches the renderer).
5. Return the validated specification wrapped in an :class:`AgentResult`.

Invalid AI output (malformed JSON or schema violations) is handled safely: the
agent retries with a repair prompt and, if it still cannot produce a valid
spec, raises :class:`~app.core.exceptions.PlanningError`.  No AI model is
hard-coded and no paid API is called during tests (the LLM client is injected).

Critic and Revision agents are **not** implemented here — this phase only plans.
"""

from __future__ import annotations

import json
from typing import Any, List, Optional

from app.agents.base import AgentBase, AgentContext, AgentResult
from app.core.exceptions import AgentError, PlanningError
from app.models.schemas import VisualRequest
from app.models.visual_spec import VisualSpecification

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT: str = """\
You are a meticulous visual-design planning assistant.  Convert the user's
request into a single JSON object that strictly matches the VisualSpecification
schema below.  Output ONLY the JSON object — no prose, no code fences, no
explanations.

Schema (all field names are exact; use snake_case):
{
  "title": string (1-200 chars, required),
  "layout": {"width": number, "height": number, "background": hex_color, "padding": number},
  "title_font_size": number,
  "title_fill": hex_color,
  "sections": [{"title": string, "x": number, "y": number, "width": number, "height": number, "fill": hex_color, "stroke": hex_color, "stroke_width": number, "text_color": hex_color, "description": string?}],
  "text": [{"text": string, "x": number, "y": number, "font_size": number, "fill": hex_color, "align": "left"|"center"|"right"}],
  "shapes": [{"type": "rect"|"rounded_rect"|"circle"|"ellipse"|"line"|"polyline"|"polygon", "x": number, "y": number, "width": number, "height": number, "cx": number, "cy": number, "r": number, "rx": number, "ry": number, "x1": number, "y1": number, "x2": number, "y2": number, "points": string, "fill": hex_color, "stroke": hex_color, "stroke_width": number, "opacity": number}],
  "arrows": [{"x1": number, "y1": number, "x2": number, "y2": number, "stroke": hex_color, "stroke_width": number, "marker": boolean}],
  "nodes": [{"id": string, "label": string, "x": number, "y": number, "width": number, "height": number, "fill": hex_color, "stroke": hex_color, "stroke_width": number, "font_size": number, "shape": "rect"|"circle"|"rounded_rect"}],
  "connections": [{"source": string, "target": string, "stroke": hex_color, "stroke_width": number}]
}

Constraints:
- All coordinates and dimensions are numbers; width/height must be positive.
- Colors are hex strings like "#2563eb" or "rgb(37,99,235)".
- Each shape must provide the geometry its type requires.
- Every "connections" source and target must match an existing node "id".

Visual type requested: {visual_type}. Complexity: {complexity}.

User prompt: {prompt}
"""


class VisualPlannerAgent(AgentBase):
    """Convert a user prompt into a :class:`VisualSpecification` via an LLM."""

    def __init__(
        self,
        text_generator: Optional[Any] = None,
        max_retries: int = 3,
    ) -> None:
        super().__init__(name="VisualPlannerAgent", text_generator=text_generator)
        self._max_retries: int = max_retries

    # ── Public API ────────────────────────────────────────────────────────

    async def run(self, context: AgentContext) -> AgentResult:
        """Run the planner and return a validated specification.

        Returns
        -------
        AgentResult
            ``success=True`` with ``data`` set to the
            :class:`VisualSpecification` on success; ``success=False`` with an
            ``error`` message otherwise.
        """
        request: Optional[VisualRequest] = context.request
        if request is None:
            return AgentResult.fail("No VisualRequest found in context.")

        if not self.has_provider:
            return AgentResult.fail(
                "No LLM provider is configured for the VisualPlannerAgent."
            )

        try:
            spec: VisualSpecification = await self._plan(request)
        except PlanningError:
            raise
        except AgentError:
            raise
        except Exception as exc:  # noqa: BLE001 — surface as a planning error
            raise PlanningError(f"Visual planning failed: {exc}") from exc

        return AgentResult.ok(
            data=spec,
            visual_spec=spec,
            status="planning",
        )

    # ── Planning ──────────────────────────────────────────────────────────

    async def _plan(self, request: VisualRequest) -> VisualSpecification:
        """Generate, parse and validate a specification from *request*."""
        # The full schema instructions (+ the user's request) live in the
        # system prompt; the user message is a short trigger that points the
        # model at the schema.
        system_prompt: str = SYSTEM_PROMPT.format(
            visual_type=request.visual_type.value,
            complexity=request.complexity.value,
            prompt=request.prompt,
        )
        user_message: str = (
            "Produce a single JSON object matching the VisualSpecification "
            "schema described in the system prompt. Output ONLY the JSON — "
            "no prose, no code fences, no explanations."
        )

        last_error: Optional[str] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                raw = await self._generate_text(
                    user_message,
                    system_prompt=system_prompt,
                    temperature=0.2,
                    max_tokens=4000,
                )
                return self._parse_spec(raw)
            except PlanningError:
                raise
            except (ValueError, AgentError) as exc:
                # ValueError covers JSONDecodeError and pydantic.ValidationError;
                # AgentError covers underlying provider/network failures.
                last_error = str(exc)
                if attempt < self._max_retries:
                    # Retry with a repair instruction appended to the prompt.
                    system_prompt = self._repair_prompt(system_prompt, last_error)
                    continue
                raise PlanningError(
                    f"LLM failed to produce a valid VisualSpecification after "
                    f"{self._max_retries} attempts: {last_error}"
                ) from exc

        # Unreachable, but keeps linters happy.
        raise PlanningError(
            f"LLM failed to produce a valid VisualSpecification: {last_error}"
        )

    # ── Parsing & validation ──────────────────────────────────────────────

    def _parse_spec(self, raw: str) -> VisualSpecification:
        """Extract and validate JSON from a possibly-noisy LLM response."""
        text = (raw or "").strip()
        if not text:
            raise ValueError("LLM returned an empty response.")

        # Strip surrounding markdown code fences (with optional language tag).
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()

        # If there is surrounding prose, isolate the JSON object.
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError(
                    "Could not locate a JSON object in the LLM response."
                )
            text = text[start : end + 1]

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc.msg}") from exc

        if not isinstance(data, dict):
            raise ValueError("The parsed JSON is not an object.")

        # Validate against the schema — the safety net.
        return VisualSpecification.model_validate(data)

    # ── Prompt repair ─────────────────────────────────────────────────────

    def _repair_prompt(self, base_prompt: str, error: str) -> str:
        """Append a repair instruction so the next attempt is self-correcting."""
        return (
            base_prompt
            + "\n\nThe previous response was invalid. "
            f"Problem: {error}\n"
            "Return ONLY valid JSON matching the schema above, "
            "with no prose, code fences, or extra text."
        )

    # ── System prompt (kept for reference / external reuse) ──────────────

    @staticmethod
    def system_prompt() -> str:
        """Return the system prompt used by the planner."""
        return SYSTEM_PROMPT


# Re-exported for convenience / type checking.
__all__ = ["VisualPlannerAgent", "SYSTEM_PROMPT"]
