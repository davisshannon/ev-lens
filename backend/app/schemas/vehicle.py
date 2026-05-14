from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class VehicleOut(BaseModel):
    id: UUID
    provider: str
    provider_vehicle_id: str
    vin: str | None
    display_name: str | None
    model: str | None
    year: int | None
    timezone: str
    nominal_battery_kwh: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SnapshotOut(BaseModel):
    id: int
    vehicle_id: UUID
    observed_at: datetime
    battery_level: float | None
    usable_battery_level: float | None
    battery_range_km: float | None
    est_battery_range_km: float | None
    charging_state: str | None
    charge_limit_soc: float | None
    charger_power_kw: float | None
    charger_voltage: int | None
    charger_actual_current: int | None
    charger_phases: int | None
    plugged_in: bool | None
    latitude: float | None
    longitude: float | None
    speed_kmh: float | None
    odometer_km: float | None
    vehicle_state: str | None
    inside_temp_c: float | None
    outside_temp_c: float | None
    climate_on: bool | None
    sentry_mode: bool | None
    locked: bool | None

    model_config = {"from_attributes": True}


class ProviderHealthOut(BaseModel):
    healthy: bool
    last_success_at: datetime | None
    last_error: str | None
    recent_errors: int


class TeslaAuthUrlOut(BaseModel):
    auth_url: str
    state: str
