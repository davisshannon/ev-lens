import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ChargeSession(Base):
    __tablename__ = "charge_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id"))
    tariff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tariffs.id"))

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    start_soc: Mapped[float | None] = mapped_column(Numeric(5, 2))
    end_soc: Mapped[float | None] = mapped_column(Numeric(5, 2))
    charge_limit_soc: Mapped[float | None] = mapped_column(Numeric(5, 2))

    battery_kwh_added: Mapped[float | None] = mapped_column(Numeric(8, 3))
    wall_kwh_estimated: Mapped[float | None] = mapped_column(Numeric(8, 3))
    # Populated from Wall Connector telemetry when available
    wall_kwh_actual: Mapped[float | None] = mapped_column(Numeric(8, 3))

    avg_power_kw: Mapped[float | None] = mapped_column(Numeric(6, 2))
    max_power_kw: Mapped[float | None] = mapped_column(Numeric(6, 2))
    avg_voltage: Mapped[int | None]
    phases: Mapped[int | None]
    charge_efficiency: Mapped[float | None] = mapped_column(Numeric(5, 4))

    cost_estimated: Mapped[float | None] = mapped_column(Numeric(8, 4))
    cost_currency: Mapped[str | None] = mapped_column(String(3))

    # Energy source breakdown (from Powerwall if available)
    grid_kwh: Mapped[float | None] = mapped_column(Numeric(8, 3))
    solar_kwh: Mapped[float | None] = mapped_column(Numeric(8, 3))
    powerwall_kwh: Mapped[float | None] = mapped_column(Numeric(8, 3))
    energy_source: Mapped[str | None] = mapped_column(String(16))  # grid/solar/powerwall/mixed

    # Session quality flags
    has_gap: Mapped[bool] = mapped_column(Boolean, default=False)
    incomplete: Mapped[bool] = mapped_column(Boolean, default=False)
    invalid: Mapped[bool] = mapped_column(Boolean, default=False)
    invalid_reason: Mapped[str | None] = mapped_column(String(128))

    # Import tracking
    imported_from: Mapped[str | None] = mapped_column(String(32))  # teslamate/etc

    raw: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_charge_sessions_vehicle_started", "vehicle_id", "started_at"),
        Index("ix_charge_sessions_started_brin", "started_at", postgresql_using="brin"),
        # Deduplication constraint
        Index("ix_charge_sessions_vehicle_started_unique", "vehicle_id", "started_at", unique=True),
    )


class ChargePlan(Base):
    __tablename__ = "charge_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    tariff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tariffs.id"))
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("charge_sessions.id"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    departure_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    current_soc: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    target_soc: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    recommended_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recommended_stop: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    expected_kwh: Mapped[float | None] = mapped_column(Numeric(8, 3))
    expected_cost: Mapped[float | None] = mapped_column(Numeric(8, 4))
    expected_cost_currency: Mapped[str | None] = mapped_column(String(3))

    # Post-charge actuals (populated after session completes)
    actual_kwh: Mapped[float | None] = mapped_column(Numeric(8, 3))
    actual_cost: Mapped[float | None] = mapped_column(Numeric(8, 4))
    actual_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_stop: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    confidence: Mapped[str] = mapped_column(String(16), default="moderate")  # low/moderate/high
    explanation: Mapped[list | None] = mapped_column(ARRAY(Text))

    inputs: Mapped[dict | None] = mapped_column(JSONB)
    result: Mapped[dict | None] = mapped_column(JSONB)
