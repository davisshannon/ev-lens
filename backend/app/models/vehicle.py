import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_vehicle_id: Mapped[str] = mapped_column(String(256), nullable=False)
    vin: Mapped[str | None] = mapped_column(String(17))
    display_name: Mapped[str | None] = mapped_column(String(256))
    model: Mapped[str | None] = mapped_column(String(128))
    year: Mapped[int | None]
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    nominal_battery_kwh: Mapped[float | None] = mapped_column(Numeric(6, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    snapshots: Mapped[list["VehicleSnapshot"]] = relationship(back_populates="vehicle")
    provider_events: Mapped[list["ProviderEvent"]] = relationship(back_populates="vehicle")

    __table_args__ = (
        Index("ix_vehicles_provider_provider_vehicle_id", "provider", "provider_vehicle_id", unique=True),
    )


class VehicleSnapshot(Base):
    __tablename__ = "vehicle_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # State of Charge
    battery_level: Mapped[float | None] = mapped_column(Numeric(5, 2))  # total %
    usable_battery_level: Mapped[float | None] = mapped_column(Numeric(5, 2))  # usable %
    battery_range_km: Mapped[float | None] = mapped_column(Numeric(7, 2))
    est_battery_range_km: Mapped[float | None] = mapped_column(Numeric(7, 2))
    ideal_battery_range_km: Mapped[float | None] = mapped_column(Numeric(7, 2))

    # Location
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    heading: Mapped[int | None]
    speed_kmh: Mapped[float | None] = mapped_column(Numeric(6, 2))
    odometer_km: Mapped[float | None] = mapped_column(Numeric(10, 2))

    # Charging
    charging_state: Mapped[str | None] = mapped_column(String(32))
    charge_limit_soc: Mapped[float | None] = mapped_column(Numeric(5, 2))
    charger_power_kw: Mapped[float | None] = mapped_column(Numeric(6, 2))
    charger_voltage: Mapped[int | None]
    charger_actual_current: Mapped[int | None]
    charger_phases: Mapped[int | None]
    plugged_in: Mapped[bool | None]
    scheduled_charging_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Climate / Environment
    inside_temp_c: Mapped[float | None] = mapped_column(Numeric(4, 1))
    outside_temp_c: Mapped[float | None] = mapped_column(Numeric(4, 1))
    climate_on: Mapped[bool | None]
    is_preconditioning: Mapped[bool | None]

    # Vehicle state
    vehicle_state: Mapped[str | None] = mapped_column(String(32))  # online/asleep/offline
    sentry_mode: Mapped[bool | None]
    locked: Mapped[bool | None]
    is_user_present: Mapped[bool | None]

    # Raw provider payload preserved for replay testing
    raw: Mapped[dict | None] = mapped_column(JSONB)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="snapshots")

    __table_args__ = (
        # Primary query pattern: latest snapshot for a vehicle
        Index("ix_snapshots_vehicle_observed", "vehicle_id", "observed_at"),
        # BRIN index for time-range scans across all vehicles
        Index("ix_snapshots_observed_brin", "observed_at", postgresql_using="brin"),
    )


class ProviderEvent(Base):
    __tablename__ = "provider_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)  # poll_success/poll_error/rate_limit/auth_error
    severity: Mapped[str] = mapped_column(String(16), default="info")  # info/warning/error
    message: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict | None] = mapped_column(JSONB)

    vehicle: Mapped["Vehicle | None"] = relationship(back_populates="provider_events")

    __table_args__ = (
        Index("ix_provider_events_vehicle_occurred", "vehicle_id", "occurred_at"),
    )
