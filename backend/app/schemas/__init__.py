"""
API schema package.

Re-exports request and response Pydantic models for convenient access:
``from app.schemas import GenerationRequest, HealthResponse``.
"""

from app.schemas.request import GenerationRequest, GenerationStatusRequest
from app.schemas.response import (
    BaseResponse,
    ErrorResponse,
    GenerationResponse,
    GenerationStatusResponse,
    HealthResponse,
)

__all__ = [
    "BaseResponse",
    "ErrorResponse",
    "GenerationRequest",
    "GenerationResponse",
    "GenerationStatusRequest",
    "GenerationStatusResponse",
    "HealthResponse",
]
