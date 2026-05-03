from datetime import datetime
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


RiskLevel = Literal["Green", "Yellow", "Red"]


class RoutingRequest(FeasibilityRequest):
    pass


class RouteSegment(BaseModel):
    coordinates: list[list[float]] = Field(
        ...,
        description="Line segment coordinates in [latitude, longitude] format.",
    )
    risk_level: RiskLevel
    is_gap: bool


class RoutingAlert(BaseModel):
    location: list[float] = Field(
        ...,
        description="Alert location in [latitude, longitude] format.",
    )
    level: RiskLevel
    message: str


class RoutingOption(BaseModel):
    label: str
    provider: str
    route_geometry: dict | None = None
    route_segments: list[RouteSegment] = Field(default_factory=list)
    gap_segments: list[RouteSegment] = Field(default_factory=list)
    alerts: list[RoutingAlert] = Field(default_factory=list)
    distance_km: float | None = None
    duration_min: float | None = None
    score: int | None = None
    is_supported_area: bool = True
    warning_message: str | None = None
    explanations: list[FeasibilityExplanation] = Field(default_factory=list)


class RoutingResponse(BaseModel):
    route_geometry: dict | None = None
    route_segments: list[RouteSegment] = Field(default_factory=list)
    gap_segments: list[RouteSegment] = Field(default_factory=list)
    alerts: list[RoutingAlert] = Field(default_factory=list)
    alerts_status_message: str | None = None
    distance_km: float | None = None
    duration_min: float | None = None
    route_options: list[RoutingOption] = Field(default_factory=list)
    score: int | None = None
    is_supported_area: bool = True
    warning_message: str | None = None
    explanations: list[FeasibilityExplanation] = Field(default_factory=list)
    debug_signature: str | None = None


class MelbourneHeatmapRegion(BaseModel):
    sa2_code: str
    suburb_name: str
    score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    intensity: int = Field(..., ge=0, le=100)
    working_population_ratio: float
    short_commute_pct: float
    zero_car_household_pct: float
    geometry: dict | None = None


class MelbourneHeatmapResponse(BaseModel):
    regions: list[MelbourneHeatmapRegion] = Field(default_factory=list)
    status_message: str | None = None


class ReportCreateRequest(BaseModel):
    user_id: str = Field(..., description="Stable client-generated UUID stored in localStorage.")
    latitude: float = Field(..., description="Reported gap latitude in WGS84.")
    longitude: float = Field(..., description="Reported gap longitude in WGS84.")
    issue_type: str = Field(default="gap", description="Issue type. Current frontend should send `gap`.")
    description: str | None = Field(default=None, description="Optional user-supplied report details.")

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("user_id must not be empty.")
        return value

    @field_validator("latitude")
    @classmethod
    def validate_report_latitude(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90.")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_report_longitude(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180.")
        return value


class ReportResponse(BaseModel):
    report_id: str
    user_id: str
    segment_id: str | None = None
    issue_type: str
    status: str
    latitude: float
    longitude: float
    description: str | None = None
    reported_at: datetime


class ReportListResponse(BaseModel):
    reports: list[ReportResponse] = Field(default_factory=list)
