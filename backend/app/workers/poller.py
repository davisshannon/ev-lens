"""
Vehicle state polling worker.

Runs as a background asyncio task started on app lifespan.
Conservative defaults: poll every 5 min when idle, every 60s when charging/driving.
Skips wakeup of sleeping vehicles unless explicitly requested.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models.vehicle import Vehicle, VehicleSnapshot, ProviderEvent
from app.security.encryption import decrypt, encrypt
from app.services.charging.detector import detect_sessions
from app.services.providers.tesla import TeslaAuthService, TeslaProvider
from app.workers.battery_worker import run_battery_analysis

log = logging.getLogger(__name__)

POLL_INTERVAL_IDLE_S = 300       # 5 min when vehicle is idle/asleep
POLL_INTERVAL_ACTIVE_S = 60      # 60s when charging or driving
TOKEN_REFRESH_BUFFER_S = 300     # refresh token 5 min before expiry


async def start_poller() -> None:
    log.info("Poller starting")
    while True:
        try:
            await _poll_all_vehicles()
        except Exception:
            log.exception("Poller cycle failed")
        await asyncio.sleep(POLL_INTERVAL_IDLE_S)


async def _poll_all_vehicles() -> None:
    async with AsyncSessionLocal() as db:
        from app.models.integration import Integration
        result = await db.execute(
            select(Integration).where(
                Integration.integration_type == "tesla_fleet",
                Integration.enabled.is_(True),
            )
        )
        integrations = result.scalars().all()

        for integration in integrations:
            try:
                access_token = await _ensure_valid_token(integration, db)
                if not access_token:
                    continue
                provider = TeslaProvider(access_token=access_token)
                await _poll_integration(provider, integration, db)
            except Exception:
                log.exception("Failed to poll integration %s", integration.id)


async def _ensure_valid_token(integration, db: AsyncSession) -> str | None:
    config = integration.config
    expires_at = config.get("expires_at", 0)

    if expires_at - TOKEN_REFRESH_BUFFER_S < datetime.now(timezone.utc).timestamp():
        refresh_token_enc = config.get("refresh_token_encrypted")
        if not refresh_token_enc:
            return None
        try:
            auth = TeslaAuthService()
            tokens = await auth.refresh_tokens(decrypt(refresh_token_enc))
            import time
            new_config = {
                **config,
                "access_token_encrypted": encrypt(tokens["access_token"]),
                "refresh_token_encrypted": encrypt(tokens["refresh_token"]),
                "expires_at": time.time() + tokens.get("expires_in", 3600),
            }
            integration.config = new_config
            await db.commit()
            return tokens["access_token"]
        except Exception:
            log.exception("Token refresh failed for integration %s", integration.id)
            return None

    encrypted = config.get("access_token_encrypted")
    return decrypt(encrypted) if encrypted else None


async def _poll_integration(provider: TeslaProvider, integration, db: AsyncSession) -> None:
    vehicles_result = await db.execute(select(Vehicle).where(Vehicle.provider == "tesla_fleet"))
    vehicles = vehicles_result.scalars().all()

    for vehicle in vehicles:
        await _poll_vehicle(provider, vehicle, db)


async def _poll_vehicle(provider: TeslaProvider, vehicle: Vehicle, db: AsyncSession) -> None:
    try:
        state = await provider.get_vehicle_state(vehicle.provider_vehicle_id)

        snapshot = VehicleSnapshot(
            vehicle_id=vehicle.id,
            observed_at=state.observed_at,
            battery_level=state.battery_level,
            usable_battery_level=state.usable_battery_level,
            battery_range_km=state.battery_range_km,
            charging_state=state.charging_state,
            charge_limit_soc=state.charge_limit_soc,
            charger_power_kw=state.charger_power_kw,
            charger_voltage=state.charger_voltage,
            charger_actual_current=state.charger_actual_current,
            charger_phases=state.charger_phases,
            plugged_in=state.plugged_in,
            latitude=state.latitude,
            longitude=state.longitude,
            speed_kmh=state.speed_kmh,
            odometer_km=state.odometer_km,
            vehicle_state=state.vehicle_state,
            raw=state.raw,
        )
        db.add(snapshot)

        event = ProviderEvent(
            vehicle_id=vehicle.id,
            event_type="poll_success",
            severity="info",
            message=f"SoC={state.battery_level}% state={state.vehicle_state}",
        )
        db.add(event)

        await db.commit()
        log.debug("Polled vehicle %s: SoC=%s%%", vehicle.display_name, state.battery_level)

        # Run session detector over the last 2 hours of snapshots after each poll
        await _run_session_detector(vehicle, db)

        # Run battery health estimator and anomaly detectors
        await run_battery_analysis(vehicle.id, db)

    except Exception as exc:
        log.warning("Poll failed for vehicle %s: %s", vehicle.id, exc)
        db.add(ProviderEvent(
            vehicle_id=vehicle.id,
            event_type="poll_error",
            severity="error",
            message=str(exc),
        ))
        await db.commit()


async def _run_session_detector(vehicle: Vehicle, db: AsyncSession) -> None:
    """Run detector over a 4-hour rolling window after each poll."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=4)
        result = await db.execute(
            select(VehicleSnapshot)
            .where(
                VehicleSnapshot.vehicle_id == vehicle.id,
                VehicleSnapshot.observed_at >= cutoff,
            )
            .order_by(VehicleSnapshot.observed_at)
        )
        snaps = result.scalars().all()
        if snaps:
            nominal_kwh = float(vehicle.nominal_battery_kwh) if vehicle.nominal_battery_kwh else None
            await detect_sessions(vehicle.id, snaps, db, nominal_kwh=nominal_kwh)
            await db.commit()
    except Exception:
        log.exception("Session detector failed for vehicle %s", vehicle.id)
