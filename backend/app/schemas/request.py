"""
Pydantic request schemas for the API layer.

These validate incoming JSON payloads before they reach the application
or domain layer.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.models.schemas import Complexity, VisualType


class GenerationRequest(BaseModel):
    """Payload sent by the frontend when the user clicks *Generate Visual*."""

    prompt: str = Field(..., min_length=1, max_length=5000, description="The user's visual description.")
    visual_type: VisualType = Field(
        default=VisualType.AUTO,
        description="Type of visual to generate.",
    )
    complexity: Complexity = Field(
        default=Complexity.MEDIUM,
        description="Complexity level of the visual.",
    )

    @field_validator("prompt")
    @classmethod
    def _validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Prompt must not be empty or whitespace only.")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "Create an infographic about the benefits of solar energy for residential homeowners.",
                "visual_type": "infographic",
                "complexity": "medium",
            }
        }
    }


class GenerationStatusRequest(BaseModel):
    """Optional payload for checking / cancelling a generation by request_id."""

    request_id: str = Field(..., min_length=1, description="Unique identifier of the generation request.")
