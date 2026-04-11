from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ImpactLevel = Literal["Low", "Medium", "High"]


class FeasibilityRequest(BaseModel):
    start_lat: float = Field(..., description="Start latitude in WGS84.")
    start_lng: float = Field(..., description="Start longitude in WGS84.")
    end_lat: float = Field(..., description="Destination latitude in WGS84.")
    end_lng: float = Field(..., description="Destination longitude in WGS84.")

    @field_validator("start_lat", "end_lat")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90.")
        return value

    @field_validator("start_lng", "end_lng")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180.")
        return value

    @model_validator(mode="after")
    def validate_distinct_points(self) -> "FeasibilityRequest":
        if self.start_lat == self.end_lat and self.start_lng == self.end_lng:
            raise ValueError("Start and destination must not be identical.")
        return self


class FeasibilityExplanation(BaseModel):
    factor: str
    impact: ImpactLevel


class FeasibilityResponse(BaseModel):
    score: int | None = Field(
        default=None,
        description="Cycling feasibility score from 0 to 100. Null when unsupported.",
    )
    is_supported_area: bool
    warning_message: str | None = None
    explanations: list[FeasibilityExplanation] = Field(default_factory=list)
