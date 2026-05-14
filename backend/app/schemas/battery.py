from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BatteryEstimateOut(BaseModel):
    id: UUID
    vehicle_id: UUID
    calculated_at: datetime
    estimated_usable_kwh: float
    nominal_kwh: float | None
    degradation_pct: float | None
    confidence: str
    sessions_used: int
    explanation: list[str] | None

    model_config = {"from_attributes": True}


class AlertOut(BaseModel):
    id: UUID
    vehicle_id: UUID
    detected_at: datetime
    resolved_at: datetime | None
    alert_type: str
    severity: str
    confidence: str
    status: str
    title: str
    summary: str
    evidence: list[str] | None
    possible_causes: list[str] | None
    recommended_actions: list[str] | None

    model_config = {"from_attributes": True}


class DriveSessionOut(BaseModel):
    """Derived from snapshot windows where vehicle was moving."""
    started_at: datetime
    ended_at: datetime
    distance_km: float | None
    energy_kwh: float | None
    efficiency_wh_per_km: float | None
    start_soc: float | None
    end_soc: float | None
    max_speed_kmh: float | None
    duration_minutes: float


class CostSummaryOut(BaseModel):
    period: str              # e.g. "2026-05"
    total_cost: float
    total_kwh: float
    currency: str
    session_count: int
    avg_cost_per_kwh: float | None
    avg_cost_per_100km: float | None
    solar_kwh: float
    grid_kwh: float
    solar_pct: float
