"""
Tesla Fleet API provider.

Auth flow:
1. GET /api/v1/auth/tesla/url  → redirect user to Tesla OAuth
2. Tesla calls auth.ev-lens.com/callback?code=...&state=...
3. Bridge redirects to POST /api/v1/auth/tesla/callback with {code, state}
4. We exchange code for tokens, encrypt, store in integrations table
5. Background worker polls vehicle state on schedule
"""

import hashlib
import hmac as hmac_lib
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.services.providers.base import VehicleInfo, VehicleProvider, VehicleState

TESLA_AUTH_BASE = "https://auth.tesla.com/oauth2/v3"
TESLA_API_BASE = "https://fleet-api.prd.na.vn.cloud.tesla.com"
TESLA_TOKEN_URL = f"{TESLA_AUTH_BASE}/token"

# Scopes needed: read vehicle state, no write/command scopes for MVP
REQUIRED_SCOPES = "openid offline_access vehicle_device_data vehicle_location"


class TeslaProvider(VehicleProvider):
    """Tesla Fleet API provider. Tokens are managed externally (see TeslaAuthService)."""

    def __init__(self, access_token: str) -> None:
        self._token = access_token

    async def list_vehicles(self) -> list[VehicleInfo]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{TESLA_API_BASE}/api/1/vehicles",
                headers=self._auth_headers(),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            VehicleInfo(
                provider_vehicle_id=str(v["id"]),
                vin=v.get("vin"),
                display_name=v.get("display_name"),
                model=_infer_model(v.get("vin", "")),
                year=_infer_year(v.get("vin", "")),
            )
            for v in data.get("response", [])
        ]

    async def get_vehicle_state(self, provider_vehicle_id: str) -> VehicleState:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{TESLA_API_BASE}/api/1/vehicles/{provider_vehicle_id}/vehicle_data",
                headers=self._auth_headers(),
                params={"endpoints": "charge_state;drive_state;climate_state;vehicle_state"},
                timeout=20,
            )
            resp.raise_for_status()
            raw = resp.json().get("response", {})

        charge = raw.get("charge_state", {})
        drive = raw.get("drive_state", {})
        climate = raw.get("climate_state", {})
        state = raw.get("vehicle_state", {})

        return VehicleState(
            provider_vehicle_id=provider_vehicle_id,
            observed_at=datetime.fromtimestamp(
                drive.get("timestamp", time.time()) / 1000, tz=timezone.utc
            ),
            battery_level=charge.get("battery_level"),
            usable_battery_level=charge.get("usable_battery_level"),
            battery_range_km=_miles_to_km(charge.get("battery_range")),
            charging_state=charge.get("charging_state"),
            charge_limit_soc=charge.get("charge_limit_soc"),
            charger_power_kw=charge.get("charger_power"),
            charger_voltage=charge.get("charger_voltage"),
            charger_actual_current=charge.get("charger_actual_current"),
            charger_phases=charge.get("charger_phases"),
            plugged_in=charge.get("charging_state") != "Disconnected",
            latitude=drive.get("latitude"),
            longitude=drive.get("longitude"),
            speed_kmh=_mph_to_kmh(drive.get("speed")),
            odometer_km=_miles_to_km(state.get("odometer")),
            vehicle_state=raw.get("state"),
            raw=raw,
        )

    async def is_healthy(self) -> bool:
        try:
            await self.list_vehicles()
            return True
        except Exception:
            return False

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}


class TeslaAuthService:
    """Handles the Fleet API OAuth2 PKCE flow via the ev-lens auth bridge."""

    def generate_auth_url(self) -> tuple[str, str]:
        """
        Returns (auth_url, state).

        Routes through the EV Lens OAuth bridge at OAUTH_BRIDGE_URL/authorize.
        The bridge appends the instance URL to state (signed), redirects to Tesla,
        then forwards the code back to this instance at /api/v1/auth/tesla/callback.
        """
        state = secrets.token_urlsafe(32)
        # Bridge endpoint — it handles the Tesla redirect_uri registration
        params = {
            "instance": settings.app_public_url,
            "state": state,
        }
        return f"{settings.oauth_bridge_url}/authorize?{urlencode(params)}", state

    async def exchange_code(self, code: str) -> dict:
        """Exchange auth code for access + refresh tokens.
        redirect_uri must match exactly what the bridge registered with Tesla."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TESLA_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.tesla_client_id,
                    "client_secret": settings.tesla_client_secret,
                    "code": code,
                    "redirect_uri": f"{settings.oauth_bridge_url}/callback",
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()

    async def refresh_tokens(self, refresh_token: str) -> dict:
        """Refresh an expired access token."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TESLA_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.tesla_client_id,
                    "refresh_token": refresh_token,
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()

    def verify_bridge_signature(self, payload: str, signature: str) -> bool:
        """Verify HMAC signature from the OAuth bridge to prevent token injection."""
        expected = hmac_lib.new(
            settings.secret_key.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return hmac_lib.compare_digest(expected, signature)


def _miles_to_km(miles: float | None) -> float | None:
    return round(miles * 1.60934, 2) if miles is not None else None


def _mph_to_kmh(mph: float | None) -> float | None:
    return round(mph * 1.60934, 2) if mph is not None else None


def _infer_model(vin: str) -> str | None:
    if not vin or len(vin) < 4:
        return None
    model_map = {"S": "Model S", "3": "Model 3", "X": "Model X", "Y": "Model Y", "C": "Cybertruck"}
    return model_map.get(vin[3])


def _infer_year(vin: str) -> int | None:
    if not vin or len(vin) < 10:
        return None
    year_map = {
        "A": 2010, "B": 2011, "C": 2012, "D": 2013, "E": 2014, "F": 2015,
        "G": 2016, "H": 2017, "J": 2018, "K": 2019, "L": 2020, "M": 2021,
        "N": 2022, "P": 2023, "R": 2024, "S": 2025, "T": 2026,
    }
    return year_map.get(vin[9])
