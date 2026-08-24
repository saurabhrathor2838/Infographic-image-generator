"""
Pydantic response schemas for the API layer.

All API responses are wrapped in a consistent envelope.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Common fields present in every API response."""

    success: bool = Field(default=True, description="Whether the request succeeded.")
    timestamp: datetime = Field(default_factory=datetime.now, description="Server timestamp.")


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseResponse):
    """Response for ``GET /api/health``."""

    status: str = Field(..., description="Overall health status, e.g. 'ok'.")
    service: str = Field(..., description="Name of the service.")


# ── Generation ─────────────────────────────────────────────────────────────────

class GenerationResponse(BaseResponse):
    """Response returned when a generation request is accepted."""

    request_id: str = Field(..., description="Unique identifier for the generation request.")
    status: str = Field(..., description="Initial status of the generation.")
    message: str = Field(
        default="Generation request accepted. You can poll for status updates.",
        description="Human-readable message.",
    )
    result: Optional[dict[str, Any]] = Field(
        default=None,
        description="Result data, if available (None while generation is in progress).",
    )


class GenerationStatusResponse(BaseResponse):
    """Response for ``GET /api/generation/{request_id}``."""

    request_id: str
    status: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


# ── Error ──────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseResponse):
    """Standard error response envelope."""

    success: bool = Field(default=False)
    error: str = Field(..., description="Short error message.")
    details: Optional[str] = Field(default=None, description="Additional error details.")
