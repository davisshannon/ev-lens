import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BatteryEstimate(Base):
    __tablename__ = "battery_estimates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    estimated_usable_kwh: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    nominal_kwh: Mapped[float | None] = mapped_column(Numeric(6, 3))
    degradation_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))

    # unknown/low/moderate/high — never display health without this
    confidence: Mapped[str] = mapped_column(String(16), default="unknown")
    sessions_used: Mapped[int] = mapped_column(default=0)

    evidence: Mapped[dict | None] = mapped_column(JSONB)
    explanation: Mapped[list | None] = mapped_column(ARRAY(Text))

    __table_args__ = (
        Index("ix_battery_estimates_vehicle_calculated", "vehicle_id", "calculated_at"),
    )
