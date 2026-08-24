"""
Tests for the generation API endpoint (``POST /api/generate``).

Covers:
  - Valid requests with all fields
  - Valid requests with minimal fields (defaults)
  - Different visual_type values
  - Validation errors (empty prompt, invalid enums, oversized prompt)
  - Response schema correctness
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


# ── Valid request payloads ─────────────────────────────────────────────────

VALID_PROMPT = "Create an infographic about the benefits of solar energy."


@pytest.mark.asyncio
class TestGenerateVisual:
    """Tests for ``POST /api/generate``."""

    # ── Happy path ───────────────────────────────────────────────────────

    async def test_generate_valid_infographic(self, client: AsyncClient) -> None:
        """A valid request should return 200 with a complete response."""
        payload = {
            "prompt": VALID_PROMPT,
            "visual_type": "infographic",
            "complexity": "medium",
        }
        response = await client.post("/api/generate", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["status"] == "complete"
        assert data["visual_type"] == "infographic"
        assert data["request_id"] != ""
        assert data["message"] != ""

    async def test_generate_valid_complexity(self, client: AsyncClient) -> None:
        """A valid request with complexity_image should route correctly."""
        payload = {
            "prompt": "Create a technical diagram of a microservices architecture.",
            "visual_type": "complexity_image",
            "complexity": "high",
        }
        response = await client.post("/api/generate", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["status"] == "complete"
        assert data["visual_type"] == "complexity_image"
        assert data["request_id"] != ""

    async def test_generate_defaults(self, client: AsyncClient) -> None:
        """Omitting visual_type and complexity should use defaults (auto, medium)."""
        payload = {"prompt": VALID_PROMPT}
        response = await client.post("/api/generate", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["visual_type"] == "auto"
        assert data["message"] != ""

    async def test_generate_auto_resolved_to_infographic(self, client: AsyncClient) -> None:
        """When visual_type is 'auto', the router should default to infographic."""
        payload = {
            "prompt": VALID_PROMPT,
            "visual_type": "auto",
            "complexity": "low",
        }
        response = await client.post("/api/generate", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["visual_type"] == "auto"
        # The routing info should be in the result
        result = data["result"]
        assert result is not None
        assert result["routing"] == "infographic"

    # ── Response schema ──────────────────────────────────────────────────

    async def test_response_has_all_required_fields(self, client: AsyncClient) -> None:
        """Response must include: request_id, status, visual_type, message."""
        payload = {"prompt": VALID_PROMPT}
        response = await client.post("/api/generate", json=payload)

        assert response.status_code == 200
        data = response.json()

        required_fields = {"request_id", "status", "visual_type", "message"}
        assert required_fields.issubset(data.keys())

    async def test_response_has_timestamp_and_success(self, client: AsyncClient) -> None:
        """Response should include success and timestamp from BaseResponse."""
        payload = {"prompt": VALID_PROMPT}
        response = await client.post("/api/generate", json=payload)

        data = response.json()

        assert data["success"] is True
        assert "timestamp" in data
        assert data["timestamp"] is not None

    async def test_request_id_is_valid_uuid(self, client: AsyncClient) -> None:
        """The request_id should be a valid UUID string."""
        payload = {"prompt": VALID_PROMPT}
        response = await client.post("/api/generate", json=payload)

        data = response.json()
        request_id = data["request_id"]

        # Should be a valid UUID
        uuid.UUID(request_id)

    async def test_result_contains_plan(self, client: AsyncClient) -> None:
        """The result dict should contain a plan with routing info."""
        payload = {"prompt": VALID_PROMPT, "visual_type": "infographic", "complexity": "medium"}
        response = await client.post("/api/generate", json=payload)

        data = response.json()
        result = data["result"]

        assert result is not None
        assert "routing" in result
        assert "plan" in result
        assert "iterations" in result
        assert result["routing"] == "infographic"
        assert result["mock"] is True

    # ── Validation errors ────────────────────────────────────────────────

    async def test_empty_prompt_returns_422(self, client: AsyncClient) -> None:
        """An empty prompt should return a 422 validation error."""
        payload = {"prompt": ""}
        response = await client.post("/api/generate", json=payload)
        assert response.status_code == 422

    async def test_whitespace_prompt_returns_422(self, client: AsyncClient) -> None:
        """A whitespace-only prompt should return a 422 validation error."""
        payload = {"prompt": "   "}
        response = await client.post("/api/generate", json=payload)
        assert response.status_code == 422

    async def test_missing_prompt_returns_422(self, client: AsyncClient) -> None:
        """Omitting the prompt field entirely should return a 422 error."""
        payload = {"visual_type": "infographic", "complexity": "medium"}
        response = await client.post("/api/generate", json=payload)
        assert response.status_code == 422

    async def test_prompt_too_long_returns_422(self, client: AsyncClient) -> None:
        """A prompt exceeding 5000 characters should return a 422 error."""
        payload = {"prompt": "x" * 5001}
        response = await client.post("/api/generate", json=payload)
        assert response.status_code == 422

    async def test_invalid_visual_type_returns_422(self, client: AsyncClient) -> None:
        """An invalid visual_type value should return a 422 error."""
        payload = {"prompt": VALID_PROMPT, "visual_type": "invalid_type"}
        response = await client.post("/api/generate", json=payload)
        assert response.status_code == 422

    async def test_invalid_complexity_returns_422(self, client: AsyncClient) -> None:
        """An invalid complexity value should return a 422 error."""
        payload = {"prompt": VALID_PROMPT, "complexity": "very_complex"}
        response = await client.post("/api/generate", json=payload)
        assert response.status_code == 422

    async def test_all_complexity_levels_work(self, client: AsyncClient) -> None:
        """Low, medium, and high complexity should all succeed."""
        for level in ("low", "medium", "high"):
            payload = {
                "prompt": VALID_PROMPT,
                "visual_type": "infographic",
                "complexity": level,
            }
            response = await client.post("/api/generate", json=payload)
            assert response.status_code == 200, f"Failed for complexity={level}"

    async def test_response_is_json(self, client: AsyncClient) -> None:
        """Response content-type should be application/json."""
        payload = {"prompt": VALID_PROMPT}
        response = await client.post("/api/generate", json=payload)
        assert response.headers["content-type"] == "application/json"
