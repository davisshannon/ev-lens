"""
Polls Wall Connector and Powerwall on a 60-second schedule.
Writes HomeEnergySample rows. Enriches open charge sessions with
actual Wall Connector kWh when the session completes.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models.energy import HomeEnergySample
from app.models.integration import Integration
from app.security.encryption import decrypt
from app.services.integrations.powerwall import PowerwallClient
from app.services.integrations.wall_connector import WallConnectorClient

log = logging.getLogger(__name__)
POLL_INTERVAL_S = 60


async def start_energy_poller() -> None:
    log.info("Energy poller starting")
    while True:
        try:
            await _poll_energy()
        except Exception:
            log.exception("Energy poller cycle failed")
        await asyncio.sleep(POLL_INTERVAL_S)


async def _poll_energy() -> None:
    async with AsyncSessionLocal() as db:
        await _poll_wall_connector(db)
        await _poll_powerwall(db)
        await db.commit()


async def _poll_wall_connector(db: AsyncSession) -> None:
    result = await db.execute(
        select(Integration).where(
            Integration.integration_type == "wall_connector",
            Integration.enabled.is_(True),
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        return

    host = integration.config.get("host")
    if not host:
        return

    client = WallConnectorClient(host=host)
    vitals = await client.get_vitals()
    if not vitals:
        integration.last_error = "Unreachable"
        return

    sample = HomeEnergySample(
        observed_at=vitals.observed_at,
        source="wall_connector",
        charger_kw=vitals.power_kw if vitals.vehicle_connected else 0.0,
    )
    db.add(sample)
    integration.last_success_at = datetime.now(timezone.utc)
    integration.last_error = None


async def _poll_powerwall(db: AsyncSession) -> None:
    result = await db.execute(
        select(Integration).where(
            Integration.integration_type == "powerwall",
            Integration.enabled.is_(True),
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        return

    host = integration.config.get("host")
    password_enc = integration.config.get("password_encrypted")
    if not host or not password_enc:
        return

    password = decrypt(password_enc)
    client = PowerwallClient(host=host, password=password)
    agg = await client.get_aggregates()
    if not agg:
        integration.last_error = "Unreachable or auth failure"
        return

    sample = HomeEnergySample(
        observed_at=agg.observed_at,
        source="powerwall",
        solar_kw=agg.solar_kw,
        grid_import_kw=agg.grid_import_kw,
        grid_export_kw=agg.grid_export_kw,
        home_load_kw=agg.home_load_kw,
        battery_charge_kw=agg.battery_charge_kw,
        battery_soe_pct=agg.battery_soe_pct,
    )
    db.add(sample)
    integration.last_success_at = datetime.now(timezone.utc)
    integration.last_error = None
