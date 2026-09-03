"""
Tests for the revision API endpoints.

Covers:
  - GET /api/templates returns all 8 templates + visual types + complexities.
  - POST /api/revisions with a valid prompt returns SVG, PNG, quality report,
    and revision count.
  - POST /api/revisions with an invalid template returns 400.
  - POST /api/revisions with an empty/whitespace prompt returns 422.
  - POST /api/revisions with explicit template name works.
  - POST /api/revisions respects complexity levels.
"""

from __future__ import annotations

import base64

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestTemplatesEndpoint:
    """Tests for ``GET /api/templates``."""

    async def test_returns_all_templates(self, client: AsyncClient) -> None:
        response = await client.get("/api/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        names = [t["name"] for t in data["templates"]]
        assert "process_flow" in names
        assert "cycle" in names
        assert "timeline" in names
        assert len(data["templates"]) == 8

    async def test_templates_have_display_names(self, client: AsyncClient) -> None:
        response = await client.get("/api/templates")
        assert response.status_code == 200
        data = response.json()
        for t in data["templates"]:
            assert t["name"]
            assert t["display_name"]
            assert t["description"]

    async def test_returns_visual_types(self, client: AsyncClient) -> None:
        response = await client.get("/api/templates")
        data = response.json()
        types = [vt["value"] for vt in data["visual_types"]]
        assert "auto" in types
        assert "infographic" in types
        assert "complexity_image" in types

    async def test_returns_complexities(self, client: AsyncClient) -> None:
        response = await client.get("/api/templates")
        data = response.json()
        comps = [c["value"] for c in data["complexities"]]
        assert "low" in comps
        assert "medium" in comps
        assert "high" in comps


@pytest.mark.asyncio
class TestRevisionsEndpoint:
    """Tests for ``POST /api/revisions``."""

    async def test_valid_request_returns_svg_and_png(self, client: AsyncClient) -> None:
        response = await client.post("/api/revisions", json={
            "prompt": "Water processing workflow steps",
            "visual_type": "infographic",
            "complexity": "medium",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["svg"].startswith("<svg")
        assert data["svg"].strip().endswith("</svg>")
        assert data["png_base64"] is not None
        # Verify PNG is valid
        png_bytes = base64.b64decode(data["png_base64"])
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        assert data["quality_report"] is not None
        assert "passed" in data["quality_report"]
        assert "score" in data["quality_report"]
        assert "issues" in data["quality_report"]
        assert "warnings" in data["quality_report"]
        assert "suggestions" in data["quality_report"]
        assert isinstance(data["revisions"], int)
        assert data["revisions"] >= 0
        assert data["revisions"] <= 3
        assert isinstance(data["passed"], bool)
        assert data["template"]

    async def test_explicit_template(self, client: AsyncClient) -> None:
        response = await client.post("/api/revisions", json={
            "prompt": "Data processing workflow steps",
            "visual_type": "infographic",
            "complexity": "medium",
            "template": "process_flow",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["template"] == "process_flow"

    async def test_invalid_template_returns_400(self, client: AsyncClient) -> None:
        response = await client.post("/api/revisions", json={
            "prompt": "Test prompt",
            "template": "nonexistent_template",
        })
        assert response.status_code == 400
        data = response.json()
        assert "Unknown template" in data["detail"]

    async def test_empty_prompt_returns_422(self, client: AsyncClient) -> None:
        response = await client.post("/api/revisions", json={
            "prompt": "",
        })
        assert response.status_code == 422

    async def test_whitespace_prompt_returns_422(self, client: AsyncClient) -> None:
        response = await client.post("/api/revisions", json={
            "prompt": "   ",
        })
        assert response.status_code == 422

    @pytest.mark.parametrize("complexity", ["low", "medium", "high"])
    async def test_all_complexities(self, client: AsyncClient, complexity: str) -> None:
        response = await client.post("/api/revisions", json={
            "prompt": "Data processing workflow steps",
            "complexity": complexity,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["complexity"] == complexity
        assert data["svg"].startswith("<svg")

    @pytest.mark.parametrize("template", [
        "process_flow", "timeline", "comparison", "cycle",
        "hierarchy", "statistics", "technical_system", "step_by_step",
    ])
    async def test_all_templates(self, client: AsyncClient, template: str) -> None:
        response = await client.post("/api/revisions", json={
            "prompt": "Data processing workflow steps",
            "template": template,
            "complexity": "medium",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["template"] == template
        assert data["svg"].startswith("<svg")

    async def test_revision_count_within_bounds(self, client: AsyncClient) -> None:
        """Revision count should never exceed MAX_REVISIONS (3)."""
        response = await client.post("/api/revisions", json={
            "prompt": "Data processing workflow steps",
            "complexity": "medium",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["revisions"] <= 3

    async def test_quality_report_score_range(self, client: AsyncClient) -> None:
        response = await client.post("/api/revisions", json={
            "prompt": "Data processing workflow steps",
            "complexity": "medium",
        })
        assert response.status_code == 200
        data = response.json()
        report = data["quality_report"]
        assert 0.0 <= report["score"] <= 100.0

    async def test_no_prompt_field_errors(self, client: AsyncClient) -> None:
        """Missing prompt field should return 422."""
        response = await client.post("/api/revisions", json={
            "visual_type": "infographic",
            "complexity": "medium",
        })
        assert response.status_code == 422
