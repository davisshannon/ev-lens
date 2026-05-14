"""
Tesla Powerwall / Energy Gateway local API integration.

The Powerwall Gateway exposes a local HTTPS API. Auth requires a login
to obtain a cookie-based session. Password is the last 5 digits of the
Gateway's serial number by default.

This integration polls the aggregates endpoint to get real-time power flow
and enriches charge sessions with grid/solar/battery breakdown.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

log = logging.getLogger(__name__)

LOGIN_PATH = "/api/login/Basic"
AGGREGATES_PATH = "/api/meters/aggregates"
SOE_PATH = "/api/system_status/soe"
CONNECT_TIMEOUT = 3.0
READ_TIMEOUT = 5.0


@dataclass
class PowerwallAggregates:
    observed_at: datetime
    # Each meter: instant_power (W), energy_exported (Wh), energy_imported (Wh)
    site_instant_power_w: float    # grid: positive=import, negative=export
    battery_instant_power_w: float # battery: positive=charging, negative=discharging
    load_instant_power_w: float    # home load
    solar_instant_power_w: float   # solar generation
    battery_soe_pct: float | None  # state of energy 0–100

    @property
    def grid_import_kw(self) -> float:
        return round(max(0.0, self.site_instant_power_w) / 1000.0, 3)

    @property
    def grid_export_kw(self) -> float:
        return round(max(0.0, -self.site_instant_power_w) / 1000.0, 3)

    @property
    def solar_kw(self) -> float:
        return round(max(0.0, self.solar_instant_power_w) / 1000.0, 3)

    @property
    def battery_charge_kw(self) -> float:
        # positive = charging battery, negative = discharging
        return round(self.battery_instant_power_w / 1000.0, 3)

    @property
    def home_load_kw(self) -> float:
        return round(max(0.0, self.load_instant_power_w) / 1000.0, 3)


class PowerwallClient:
    def __init__(self, host: str, password: str, email: str = "customer@example.com") -> None:
        self._host = host.rstrip("/")
        self._password = password
        self._email = email
        self._token: str | None = None

    async def _login(self) -> bool:
        url = f"https://{self._host}{LOGIN_PATH}"
        try:
            async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(CONNECT_TIMEOUT)) as client:  # noqa: S501
                resp = await client.post(
                    url,
                    json={"username": "customer", "password": self._password, "email": self._email},
                )
                resp.raise_for_status()
                self._token = resp.json().get("token")
                return bool(self._token)
        except Exception as exc:
            log.warning("Powerwall login failed at %s: %s", self._host, exc)
            return False

    async def get_aggregates(self) -> PowerwallAggregates | None:
        if not self._token and not await self._login():
            return None

        headers = {"Authorization": f"Bearer {self._token}"}
        agg_url = f"https://{self._host}{AGGREGATES_PATH}"
        soe_url = f"https://{self._host}{SOE_PATH}"

        try:
            async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(CONNECT_TIMEOUT, read=READ_TIMEOUT)) as client:  # noqa: S501
                agg_resp = await client.get(agg_url, headers=headers)
                if agg_resp.status_code == 401:
                    self._token = None
                    if not await self._login():
                        return None
                    headers = {"Authorization": f"Bearer {self._token}"}
                    agg_resp = await client.get(agg_url, headers=headers)
                agg_resp.raise_for_status()
                agg = agg_resp.json()

                soe_resp = await client.get(soe_url, headers=headers)
                soe = soe_resp.json() if soe_resp.status_code == 200 else {}

        except Exception as exc:
            log.warning("Powerwall aggregates fetch failed: %s", exc)
            return None

        def _power(meter: str) -> float:
            return float(agg.get(meter, {}).get("instant_power", 0.0))

        return PowerwallAggregates(
            observed_at=datetime.now(timezone.utc),
            site_instant_power_w=_power("site"),
            battery_instant_power_w=_power("battery"),
            load_instant_power_w=_power("load"),
            solar_instant_power_w=_power("solar"),
            battery_soe_pct=soe.get("percentage"),
        )
