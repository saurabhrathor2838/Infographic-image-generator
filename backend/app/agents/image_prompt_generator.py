"""
Image Prompt Generator.

Takes a :class:`DesignPlan` and a :class:`VisualRequest` and produces an
:class:`ImagePrompt` — a refined, detailed prompt suitable for an image
generation model.

Future implementation: will use LLM reasoning to craft highly detailed,
style-specific prompts with negative prompts and parameter tuning.
"""

from __future__ import annotations

from app.agents.base import AgentBase, AgentContext, AgentResult
from app.core.exceptions import PromptGenerationError
from app.models.schemas import ImagePrompt


class ImagePromptGenerator(AgentBase):
    """Transforms a design plan into a detailed image-generation prompt."""

    def __init__(self, text_generator=None) -> None:
        super().__init__(name="ImagePromptGenerator", text_generator=text_generator)

    async def run(self, context: AgentContext) -> AgentResult:
        """Produce an :class:`ImagePrompt` from the design plan.

        Phase 1: constructs a prompt from design plan fields and request prompt.
        """
        design_plan = context.design_plan
        if design_plan is None:
            return AgentResult.fail("No design plan in context — run DesignPlanner first.")

        try:
            image_prompt: ImagePrompt = await self._build_prompt(context)
        except Exception as exc:
            raise PromptGenerationError(f"Prompt generation failed: {exc}") from exc

        return AgentResult.ok(
            data=image_prompt,
            image_prompt=image_prompt,
            status="generating",
        )

    async def _build_prompt(self, context: AgentContext) -> ImagePrompt:
        """Build an :class:`ImagePrompt` from available context.

        Phase 1: combines the design plan with the user prompt to create
        a basic image-generation prompt.
        """
        request = context.request
        design_plan = context.design_plan

        # Assemble the prompt from design plan components.
        palette = ", ".join(design_plan.color_palette) if design_plan.color_palette else "vibrant colors"
        elements = ", ".join(design_plan.key_elements) if design_plan.key_elements else ""

        full_prompt = (
            f"{request.prompt}. "
            f"Design layout: {design_plan.layout}. "
            f"Color palette: {palette}. "
            f"Key elements: {elements}. "
            f"Typography: {design_plan.typography.get('heading', 'clean sans-serif')} "
            f"headings, {design_plan.typography.get('body', 'readable sans-serif')} body."
        ).strip()

        negative_prompt = (
            "blur, low quality, distorted, text overlap, "
            "low resolution, watermark, signature"
        )

        return ImagePrompt(
            prompt=full_prompt,
            negative_prompt=negative_prompt,
            width=1024,
            height=1024,
            style="infographic" if request.visual_type.value == "infographic" else "technical diagram",
        )
