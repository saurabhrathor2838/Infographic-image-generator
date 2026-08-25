"""
Tests for the AI Planner Agent and ``POST /api/plan`` endpoint.

Covers:
  - ``/api/plan`` returns a valid SVG when an LLM provider is configured.
  - ``/api/plan`` returns 503 when no provider is configured.
  - ``/api/plan`` returns 422 for invalid input (empty / whitespace prompt).
  - ``/api/plan`` returns 502 when the LLM output is not valid JSON.
  - ``/api/plan`` returns 502 when the LLM output fails schema validation.
  - The mock text generator produces specs that pass schema validation.
  - The complete planner → renderer → SVG pipeline (integration).
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest
from httpx import AsyncClient

from app.agents.visual_planner import VisualPlannerAgent, SYSTEM_PROMPT
from app.agents.base import AgentContext
from app.models.schemas import VisualRequest, VisualType, Complexity
from app.models.visual_spec import VisualSpecification
from app.providers.mock_text_generator import MockTextGenerator


# ── A complete, schema-valid specification JSON string ───────────────────────

VALID_SPEC_JSON: str = json.dumps({
    "title": "Benefits of Solar Energy",
    "layout": {"width": 900, "height": 650, "background": "#0f172a", "padding": 40},
    "title_font_size": 36,
    "title_fill": "#ffffff",
    "sections": [
        {
            "title": "Overview",
            "x": 40, "y": 40, "width": 820, "height": 140,
            "fill": "#1e293b", "stroke": "#334155", "stroke_width": 1,
            "text_color": "#e2e8f0",
            "description": "Solar energy reduces electricity bills and carbon emissions.",
        }
    ],
    "text": [
        {"text": "Solar energy is clean and renewable.", "x": 450, "y": 580,
         "font_size": 16, "fill": "#cbd5e1", "align": "center"}
    ],
    "shapes": [
        {"type": "circle", "cx": 450, "cy": 440, "r": 50,
         "fill": "#F18F01", "stroke": "#1e293b", "stroke_width": 2, "opacity": 0.2}
    ],
    "nodes": [
        {"id": "n1", "label": "Cost Savings", "x": 120, "y": 260,
         "width": 160, "height": 70, "fill": "#2E86AB", "stroke": "#1e293b",
         "stroke_width": 2, "font_size": 14, "shape": "rounded_rect"},
        {"id": "n2", "label": "Environmental", "x": 320, "y": 260,
         "width": 160, "height": 70, "fill": "#A23B72", "stroke": "#1e293b",
         "stroke_width": 2, "font_size": 14, "shape": "rounded_rect"},
        {"id": "n3", "label": "Energy Independence", "x": 520, "y": 260,
         "width": 160, "height": 70, "fill": "#F18F01", "stroke": "#1e293b",
         "stroke_width": 2, "font_size": 14, "shape": "rounded_rect"},
    ],
    "connections": [
        {"source": "n1", "target": "n2", "stroke": "#64748b", "stroke_width": 2},
        {"source": "n2", "target": "n3", "stroke": "#64748b", "stroke_width": 2},
    ],
})


# ── /api/plan endpoint tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
class TestPlanEndpoint:
    """Tests for ``POST /api/plan``."""

    async def test_plan_returns_svg(self, client: AsyncClient, override_llm, make_text_generator) -> None:
        """A valid LLM response should produce an SVG document."""
        gen = make_text_generator([VALID_SPEC_JSON])
        override_llm(gen)

        payload = {
            "prompt": "Create an infographic about the benefits of solar energy.",
            "visual_type": "infographic",
            "complexity": "medium",
        }
        response = await client.post("/api/plan", json=payload)

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        svg = response.text
        assert svg.startswith("<svg")
        assert svg.strip().endswith("</svg>")
        # The SVG should contain the title from the spec.
        assert "Benefits of Solar Energy" in svg

    async def test_plan_svg_is_valid_xml(self, client: AsyncClient, override_llm, make_text_generator) -> None:
        """The returned SVG must be parseable XML."""
        gen = make_text_generator([VALID_SPEC_JSON])
        override_llm(gen)

        response = await client.post(
            "/api/plan",
            json={"prompt": "Create an infographic about solar energy.", "visual_type": "infographic", "complexity": "low"},
        )
        assert response.status_code == 200
        root = ET.fromstring(response.text)
        assert root.tag.endswith("svg")

    async def test_plan_with_auto_visual_type(self, client: AsyncClient, override_llm, make_text_generator) -> None:
        """``visual_type: auto`` should also work via /api/plan."""
        gen = make_text_generator([VALID_SPEC_JSON])
        override_llm(gen)

        response = await client.post(
            "/api/plan",
            json={"prompt": "Create an infographic about solar energy."},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"

    async def test_plan_no_provider_returns_503(self, client: AsyncClient) -> None:
        """When no LLM provider is configured, /api/plan must return 503.

        We explicitly override the FastAPI dependency to return ``None``
        so the assertion holds regardless of the environment's AI_PROVIDER
        setting.
        """
        from app.main import app
        from app.providers.factory import get_text_generator
        app.dependency_overrides[get_text_generator] = lambda: None
        try:
            response = await client.post(
                "/api/plan",
                json={"prompt": "Create an infographic about solar energy.", "visual_type": "infographic", "complexity": "medium"},
            )
            assert response.status_code == 503
            data = response.json()
            assert "not configured" in data["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_text_generator, None)

    async def test_plan_empty_prompt_returns_422(self, client: AsyncClient) -> None:
        """An empty prompt should return 422 (validation error)."""
        response = await client.post(
            "/api/plan",
            json={"prompt": "", "visual_type": "infographic", "complexity": "medium"},
        )
        assert response.status_code == 422

    async def test_plan_whitespace_prompt_returns_422(self, client: AsyncClient) -> None:
        """A whitespace-only prompt should return 422."""
        response = await client.post(
            "/api/plan",
            json={"prompt": "   ", "visual_type": "infographic", "complexity": "medium"},
        )
        assert response.status_code == 422

    async def test_plan_invalid_json_returns_502(self, client: AsyncClient, override_llm, make_text_generator) -> None:
        """When the LLM returns non-JSON, /api/plan should return 502."""
        gen = make_text_generator(["This is not valid JSON at all!"])
        override_llm(gen)

        response = await client.post(
            "/api/plan",
            json={"prompt": "Create an infographic about solar energy.", "visual_type": "infographic", "complexity": "medium"},
        )
        assert response.status_code == 502
        data = response.json()
        assert "planning failed" in data["detail"].lower()

    async def test_plan_schema_violation_returns_502(
        self, client: AsyncClient, override_llm, make_text_generator
    ) -> None:
        """When the LLM returns JSON that fails schema validation, /api/plan returns 502."""
        # Valid JSON but missing required 'title' field and invalid node refs.
        bad_json = json.dumps({"sections": [{"title": "x"}], "connections": [{"source": "a", "target": "b"}]})
        gen = make_text_generator([bad_json])
        override_llm(gen)

        response = await client.post(
            "/api/plan",
            json={"prompt": "Create an infographic about solar energy.", "visual_type": "infographic", "complexity": "medium"},
        )
        assert response.status_code == 502

    async def test_plan_retries_then_succeeds(
        self, client: AsyncClient, override_llm, make_text_generator
    ) -> None:
        """If the first LLM attempt is bad but the retry is good, /api/plan should succeed."""
        gen = make_text_generator(["not json", VALID_SPEC_JSON])
        override_llm(gen)

        response = await client.post(
            "/api/plan",
            json={"prompt": "Create an infographic about solar energy.", "visual_type": "infographic", "complexity": "medium"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"

    async def test_plan_complexity_image_returns_svg(
        self, client: AsyncClient, override_llm
    ) -> None:
        """``complexity_image`` visual type should also render to SVG via /api/plan."""
        gen = MockTextGenerator()
        override_llm(gen)

        response = await client.post(
            "/api/plan",
            json={
                "prompt": "Create a complexity image explaining cloud architecture.",
                "visual_type": "complexity_image",
                "complexity": "high",
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        svg = response.text
        assert svg.startswith("<svg")
        assert svg.strip().endswith("</svg>")
        root = ET.fromstring(svg)
        assert root.tag.endswith("svg")

    async def test_plan_low_complexity_produces_fewer_elements(
        self, client: AsyncClient, override_llm
    ) -> None:
        """Low complexity spec should produce a sparser SVG than high complexity."""
        gen = MockTextGenerator()
        override_llm(gen)

        response = await client.post(
            "/api/plan",
            json={
                "prompt": "Create an infographic explaining the water cycle.",
                "visual_type": "complexity_image",
                "complexity": "low",
            },
        )
        assert response.status_code == 200
        low_svg = response.text
        low_root = ET.fromstring(low_svg)

        response = await client.post(
            "/api/plan",
            json={
                "prompt": "Create an infographic explaining the water cycle.",
                "visual_type": "complexity_image",
                "complexity": "high",
            },
        )
        assert response.status_code == 200
        high_svg = response.text
        high_root = ET.fromstring(high_svg)

        # High complexity should have strictly more rect elements (nodes+sections+shapes)
        # and more text elements (annotations) than low complexity.
        low_rects = len(low_root.findall(".//{http://www.w3.org/2000/svg}rect"))
        high_rects = len(high_root.findall(".//{http://www.w3.org/2000/svg}rect"))
        low_texts = len(low_root.findall(".//{http://www.w3.org/2000/svg}text"))
        high_texts = len(high_root.findall(".//{http://www.w3.org/2000/svg}text"))

        assert high_rects > low_rects, (
            f"High complexity ({high_rects} rects) should have more rect elements "
            f"than low ({low_rects})"
        )
        assert high_texts > low_texts, (
            f"High complexity ({high_texts} texts) should have more text elements "
            f"than low ({low_texts})"
        )


# ── MockTextGenerator unit tests ──────────────────────────────────────────────

@pytest.mark.asyncio
class TestMockTextGenerator:
    """Tests for the development mock text generator."""

    async def test_generates_valid_spec(self) -> None:
        """The mock generator must always produce schema-valid JSON."""
        gen = MockTextGenerator()
        system_prompt = (
            SYSTEM_PROMPT
            .replace("{visual_type}", "infographic")
            .replace("{complexity}", "medium")
            .replace("{prompt}", "Create an infographic about solar energy benefits")
        )
        result = await gen.generate("trigger", system_prompt=system_prompt)
        spec_dict = json.loads(result.text)
        spec = VisualSpecification.model_validate(spec_dict)
        assert spec.title is not None
        assert len(spec.nodes) >= 1

    async def test_handles_short_prompt(self) -> None:
        """The mock generator should work with very short prompts."""
        gen = MockTextGenerator()
        result = await gen.generate("trigger", system_prompt="")
        spec = VisualSpecification.model_validate(json.loads(result.text))
        assert spec.title

    async def test_health_check(self) -> None:
        """The mock generator should report healthy."""
        gen = MockTextGenerator()
        assert await gen.health_check() is True


# ── VisualPlannerAgent integration test ──────────────────────────────────────

@pytest.mark.asyncio
class TestVisualPlannerAgentIntegration:
    """End-to-end test of the VisualPlannerAgent with the mock generator."""

    async def test_plan_to_svg_pipeline(self) -> None:
        """Full pipeline: request → planner → spec → SVG renderer."""
        gen = MockTextGenerator()
        agent = VisualPlannerAgent(text_generator=gen)
        request = VisualRequest(
            prompt="Create an infographic about the benefits of solar energy",
            visual_type=VisualType.INFOGRAPHIC,
            complexity=Complexity.MEDIUM,
        )
        ctx = AgentContext(request=request)
        result = await agent.run(ctx)

        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, VisualSpecification)

        from app.renderers.svg_renderer import SVGRenderer
        svg = SVGRenderer().render(result.data)
        assert svg.startswith("<svg")
        assert svg.strip().endswith("</svg>")

    async def test_agent_no_provider_fails_gracefully(self) -> None:
        """Without a provider, the agent should report failure (not crash)."""
        agent = VisualPlannerAgent(text_generator=None)
        request = VisualRequest(
            prompt="Create an infographic about solar energy",
            visual_type=VisualType.INFOGRAPHIC,
            complexity=Complexity.MEDIUM,
        )
        ctx = AgentContext(request=request)
        result = await agent.run(ctx)
        assert result.success is False
        assert result.error is not None


# ── Complexity scaling tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
class TestComplexityScaling:
    """Verify that the mock generator produces denser visuals for higher complexity."""

    @staticmethod
    def _make_system_prompt(complexity: str) -> str:
        """Build a system prompt that the mock generator can parse."""
        return (
            SYSTEM_PROMPT
            .replace("{visual_type}", "complexity_image")
            .replace("{complexity}", complexity)
            .replace("{prompt}", "Create an infographic explaining the water cycle.")
        )

    async def test_low_complexity_produces_simple_spec(self) -> None:
        """Low complexity → 2 nodes, 1 shape, few connections."""
        gen = MockTextGenerator()
        result = await gen.generate(
            "trigger",
            system_prompt=self._make_system_prompt("low"),
        )
        spec = VisualSpecification.model_validate(json.loads(result.text))
        assert len(spec.nodes) <= 3
        assert len(spec.shapes) <= 2
        assert len(spec.text) <= 2
        assert len(spec.connections) <= 2

    async def test_medium_complexity_produces_moderate_spec(self) -> None:
        """Medium complexity → 3-4 nodes, 2-3 shapes, moderate connections."""
        gen = MockTextGenerator()
        result = await gen.generate(
            "trigger",
            system_prompt=self._make_system_prompt("medium"),
        )
        spec = VisualSpecification.model_validate(json.loads(result.text))
        assert 2 <= len(spec.nodes) <= 4
        assert len(spec.shapes) >= 2
        assert len(spec.text) >= 2

    async def test_high_complexity_produces_dense_spec(self) -> None:
        """High complexity → 6 nodes, 5 shapes, dense connections, annotations."""
        gen = MockTextGenerator()
        result = await gen.generate(
            "trigger",
            system_prompt=self._make_system_prompt("high"),
        )
        spec = VisualSpecification.model_validate(json.loads(result.text))
        assert len(spec.nodes) >= 6
        assert len(spec.shapes) >= 4
        assert len(spec.text) >= 4
        assert len(spec.connections) >= 5
