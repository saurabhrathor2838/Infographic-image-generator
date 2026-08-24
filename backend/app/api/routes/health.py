"""
Health-check endpoint.

GET /api/health
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.schemas.response import HealthResponse

router: APIRouter = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Returns the service health status.",
)
async def health_check() -> HealthResponse:
    """Return a simple health-check response.

    Response shape::

        {
            "success": true,
            "timestamp": "...",
            "status": "ok",
            "service": "AI Visual Generator"
        }
    """
    return HealthResponse(
        status="ok",
        service="AI Visual Generator",
    )
