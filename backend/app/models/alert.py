import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # vampire_drain/charging_efficiency_drop/derating/session_interruption/poor_drive_efficiency/provider_error
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="warning")  # info/warning/critical
    confidence: Mapped[str] = mapped_column(String(16), default="moderate")  # low/moderate/high
    status: Mapped[str] = mapped_column(String(16), default="open")  # open/resolved/dismissed

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    evidence: Mapped[list | None] = mapped_column(ARRAY(Text))
    possible_causes: Mapped[list | None] = mapped_column(ARRAY(Text))
    recommended_actions: Mapped[list | None] = mapped_column(ARRAY(Text))

    context: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_alerts_vehicle_detected", "vehicle_id", "detected_at"),
        Index("ix_alerts_status", "status"),
    )
