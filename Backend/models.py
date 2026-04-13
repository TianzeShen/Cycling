from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from geoalchemy2 import Geometry


class Base(DeclarativeBase):
    pass


# These mapped tables are the main sources for Epic 1 and Epic 3.
class CyclingLane(Base):
    __tablename__ = "cycling_lane"
    __table_args__ = {"schema": "ridesmart"}

    lane_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    source: Mapped[str] = mapped_column(String(50))
    external_ref: Mapped[str | None] = mapped_column(String(100))
    is_continuous: Mapped[bool] = mapped_column(Boolean)
    geom: Mapped[str] = mapped_column(Geometry("LINESTRING", srid=4326))


class RoadSegment(Base):
    __tablename__ = "road_segment"
    __table_args__ = {"schema": "ridesmart"}

    segment_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    road_name: Mapped[str | None] = mapped_column(String(150))
    speed_limit_kmh: Mapped[int | None] = mapped_column(Integer)
    aadt_volume: Mapped[int | None] = mapped_column(Integer)
    danger_score: Mapped[float] = mapped_column(Float)
    geom: Mapped[str] = mapped_column(Geometry("LINESTRING", srid=4326))


class LaneGap(Base):
    __tablename__ = "lane_gap"
    __table_args__ = {"schema": "ridesmart"}

    gap_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    lane_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ridesmart.cycling_lane.lane_id"),
    )
    segment_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ridesmart.road_segment.segment_id"),
    )
    gap_type: Mapped[str] = mapped_column(String(50))
    distance_m: Mapped[float | None] = mapped_column(Float)
    risk_note: Mapped[str | None] = mapped_column(String(200))
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326))
    detected_at: Mapped[str] = mapped_column(DateTime)


class CrashRecord(Base):
    __tablename__ = "crash_record"
    __table_args__ = {"schema": "ridesmart"}

    crash_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    segment_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ridesmart.road_segment.segment_id"),
    )
    involves_cyclist: Mapped[bool] = mapped_column(Boolean)
    geom: Mapped[str | None] = mapped_column(Geometry("POINT", srid=4326))


class FeasibilityScoreRecord(Base):
    __tablename__ = "feasibility_score"
    __table_args__ = {"schema": "ridesmart"}

    score_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    score: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str | None] = mapped_column(Text)
