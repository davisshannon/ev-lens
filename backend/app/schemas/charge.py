from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ChargeSessionOut(BaseModel):
    id: UUID
    vehicle_id: UUID
    location_id: UUID | None
    tariff_id: UUID | None
    started_at: datetime
    ended_at: datetime | None
    start_soc: float | None
    end_soc: float | None
    charge_limit_soc: float | None
    battery_kwh_added: float | None
    wall_kwh_estimated: float | None
    wall_kwh_actual: float | None
    avg_power_kw: float | None
    max_power_kw: float | None
    avg_voltage: int | None
    phases: int | None
    charge_efficiency: float | None
    cost_estimated: float | None
    cost_currency: str | None
    grid_kwh: float | None
    solar_kwh: float | None
    powerwall_kwh: float | None
    energy_source: str | None
    has_gap: bool
    incomplete: bool
    invalid: bool
    invalid_reason: str | None
    imported_from: str | None

    model_config = {"from_attributes": True}


class ChargePlanRequest(BaseModel):
    vehicle_id: UUID
    current_soc: float
    target_soc: float
    tariff_id: UUID | None = None
    departure_time: datetime | None = None


class ChargePlanOut(BaseModel):
    id: UUID
    vehicle_id: UUID
    created_at: datetime
    current_soc: float
    target_soc: float
    departure_time: datetime | None
    recommended_start: datetime | None
    recommended_stop: datetime | None
    expected_kwh: float | None
    expected_cost: float | None
    expected_cost_currency: str | None
    actual_kwh: float | None
    actual_cost: float | None
    confidence: str
    explanation: list[str] | None

    model_config = {"from_attributes": True}


class PostChargeReportOut(BaseModel):
    plan_kwh: float
    actual_kwh: float
    kwh_delta: float
    plan_cost: float
    actual_cost: float
    cost_delta: float
    plan_start: str
    actual_start: str
    start_offset_minutes: float
    duration_minutes: float
    accuracy: str


class TariffIn(BaseModel):
    name: str
    currency: str = "USD"
    timezone: str = "UTC"
    config: dict


class TariffOut(BaseModel):
    id: UUID
    name: str
    currency: str
    timezone: str
    config: dict

    model_config = {"from_attributes": True}
