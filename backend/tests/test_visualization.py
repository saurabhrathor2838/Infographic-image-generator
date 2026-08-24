"""
Tests for the visualization API endpoints.

Covers:
  - POST /api/render returns a valid SVG for a well-formed specification.
  - POST /api/render returns 422 for an invalid specification.
  - GET /api/samples/water-cycle returns the sample SVG.
  - GET /api/samples/water-cycle/spec returns the sample JSON.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.samples import water_cycle_spec


@pytest.mark.asyncio
class TestRenderEndpoint:
    """Tests for ``POST /api/render``."""

    async def test_render_valid_spec_returns_svg(self, client: AsyncClient) -> None:
        payload = {
            "title": "Test Infographic",
            "layout": {"width": 400, "height": 300, "background": "#ffffff"},
            "text": [{"text": "Hello", "x": 200, "y": 150}],
        }
        response = await client.post("/api/render", json=payload)

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        svg = response.text
        assert svg.startswith("<svg")
        assert svg.strip().endswith("</svg>")
        assert "Test Infographic" in svg
        assert "Hello" in svg

    async def test_render_empty_title_returns_422(self, client: AsyncClient) -> None:
        response = await client.post("/api/render", json={"title": ""})
        assert response.status_code == 422

    async def test_render_invalid_shape_returns_422(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/render",
            json={"title": "T", "shapes": [{"type": "circle"}]},  # missing 'r'
        )
        assert response.status_code == 422

    async def test_render_missing_body_returns_422(self, client: AsyncClient) -> None:
        response = await client.post("/api/render", json={})
        assert response.status_code == 422


@pytest.mark.asyncio
class TestWaterCycleSample:
    """Tests for the bundled Water Cycle sample endpoints."""

    async def test_sample_svg(self, client: AsyncClient) -> None:
        response = await client.get("/api/samples/water-cycle")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        svg = response.text
        assert svg.startswith("<svg")
        assert "The Water Cycle" in svg

    async def test_sample_spec(self, client: AsyncClient) -> None:
        response = await client.get("/api/samples/water-cycle/spec")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["title"] == "The Water Cycle"
        assert len(data["nodes"]) == 6
        assert len(data["connections"]) == 6
