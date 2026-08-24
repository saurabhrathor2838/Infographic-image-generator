"""
Tests for the health-check endpoint.

Covers ``GET /api/health``.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthCheck:
    """Tests for the health-check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient) -> None:
        """GET /api/health should return HTTP 200."""
        response = await client.get("/api/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_body(self, client: AsyncClient) -> None:
        """Response body should include status and service name."""
        response = await client.get("/api/health")
        data = response.json()

        assert data["status"] == "ok"
        assert data["service"] == "AI Visual Generator"
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_health_has_timestamp(self, client: AsyncClient) -> None:
        """Response should include a server timestamp."""
        response = await client.get("/api/health")
        data = response.json()

        assert "timestamp" in data
        assert data["timestamp"] is not None

    @pytest.mark.asyncio
    async def test_health_content_type(self, client: AsyncClient) -> None:
        """Response should be JSON."""
        response = await client.get("/api/health")
        assert response.headers["content-type"] == "application/json"
