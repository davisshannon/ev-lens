from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class VehicleInfo:
    provider_vehicle_id: str
    vin: str | None
    display_name: str | None
    model: str | None
    year: int | None


@dataclass
class VehicleState:
    provider_vehicle_id: str
    observed_at: datetime
    battery_level: float | None
    usable_battery_level: float | None
    battery_range_km: float | None
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
    raw: dict


class VehicleProvider(ABC):
    """Abstract interface all vehicle data providers must implement."""

    @abstractmethod
    async def list_vehicles(self) -> list[VehicleInfo]: ...

    @abstractmethod
    async def get_vehicle_state(self, provider_vehicle_id: str) -> VehicleState: ...

    @abstractmethod
    async def is_healthy(self) -> bool: ...
