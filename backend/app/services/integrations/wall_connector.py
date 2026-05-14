"""
Tesla Wall Connector local HTTP integration.

Wall Connector Gen 3 exposes a local HTTPS API at https://<gateway-ip>/api/1/vitals
No auth required on LAN. Self-signed cert — verify=False is intentional here.

API reference: https://github.com/daphot/tesla-wall-connector-api
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

log = logging.getLogger(__name__)

VITALS_PATH = "/api/1/vitals"
CONNECT_TIMEOUT = 3.0
READ_TIMEOUT = 5.0


@dataclass
class WallConnectorVitals:
    observed_at: datetime
    contactor_closed: bool
    vehicle_connected: bool
    session_s: float              # seconds this session has been active
    grid_v: float                 # grid voltage
    grid_hz: float                # grid frequency
    vehicle_current_a: float      # current flowing to vehicle
    current_a_a: float            # phase A current
    current_b_a: float            # phase B current
    current_c_a: float            # phase C current
    current_n_a: float            # neutral current
    voltage_a_v: float
    voltage_b_v: float
    voltage_c_v: float
    relay_coil_v: float
    pcba_temp_c: float
    handle_temp_c: float
    mcu_temp_c: float
    uptime_s: float
    input_thermopile_uv: float
    prox_v: float
    pilot_high_v: float
    pilot_low_v: float
    session_energy_wh: float      # energy delivered this session
    config_status: int
    evse_state: int
    current_alerts: list[str]

    @property
    def power_kw(self) -> float:
        """Approximate power from current × voltage (phase A as proxy)."""
        if self.voltage_a_v and self.current_a_a:
            phases = sum(1 for c in [self.current_b_a, self.current_c_a] if c > 0.5) + 1
            return round(self.vehicle_current_a * self.grid_v * phases / 1000.0, 2)
        return 0.0

    @property
    def session_kwh(self) -> float:
        return round(self.session_energy_wh / 1000.0, 3)


class WallConnectorClient:
    def __init__(self, host: str) -> None:
        self._host = host.rstrip("/")

    async def get_vitals(self) -> WallConnectorVitals | None:
        url = f"https://{self._host}{VITALS_PATH}"
        try:
            async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(CONNECT_TIMEOUT, read=READ_TIMEOUT)) as client:  # noqa: S501
                resp = await client.get(url)
                resp.raise_for_status()
                d = resp.json()
        except Exception as exc:
            log.warning("Wall Connector unreachable at %s: %s", self._host, exc)
            return None

        return WallConnectorVitals(
            observed_at=datetime.now(timezone.utc),
            contactor_closed=d.get("contactor_closed", False),
            vehicle_connected=d.get("vehicle_connected", False),
            session_s=d.get("session_s", 0.0),
            grid_v=d.get("grid_v", 0.0),
            grid_hz=d.get("grid_hz", 0.0),
            vehicle_current_a=d.get("vehicle_current_a", 0.0),
            current_a_a=d.get("current_a_a", 0.0),
            current_b_a=d.get("current_b_a", 0.0),
            current_c_a=d.get("current_c_a", 0.0),
            current_n_a=d.get("current_n_a", 0.0),
            voltage_a_v=d.get("voltage_a_v", 0.0),
            voltage_b_v=d.get("voltage_b_v", 0.0),
            voltage_c_v=d.get("voltage_c_v", 0.0),
            relay_coil_v=d.get("relay_coil_v", 0.0),
            pcba_temp_c=d.get("pcba_temp_c", 0.0),
            handle_temp_c=d.get("handle_temp_c", 0.0),
            mcu_temp_c=d.get("mcu_temp_c", 0.0),
            uptime_s=d.get("uptime_s", 0.0),
            input_thermopile_uv=d.get("input_thermopile_uv", 0.0),
            prox_v=d.get("prox_v", 0.0),
            pilot_high_v=d.get("pilot_high_v", 0.0),
            pilot_low_v=d.get("pilot_low_v", 0.0),
            session_energy_wh=d.get("session_energy_wh", 0.0),
            config_status=d.get("config_status", 0),
            evse_state=d.get("evse_state", 0),
            current_alerts=d.get("current_alerts", []),
        )
