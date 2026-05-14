import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.db import get_db
from app.models.battery import BatteryEstimate
from app.models.vehicle import VehicleSnapshot
from app.schemas.battery import BatteryEstimateOut, DriveSessionOut

router = APIRouter()


@router.get("/{vehicle_id}/estimates", response_model=list[BatteryEstimateOut])
async def list_estimates(
    vehicle_id: uuid.UUID,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[BatteryEstimate]:
    result = await db.execute(
        select(BatteryEstimate)
        .where(BatteryEstimate.vehicle_id == vehicle_id)
        .order_by(BatteryEstimate.calculated_at.desc())
        .limit(min(limit, 365))
    )
    return list(result.scalars().all())


@router.get("/{vehicle_id}/estimates/latest", response_model=BatteryEstimateOut)
async def get_latest_estimate(
    vehicle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> BatteryEstimate:
    result = await db.execute(
        select(BatteryEstimate)
        .where(BatteryEstimate.vehicle_id == vehicle_id)
        .order_by(BatteryEstimate.calculated_at.desc())
        .limit(1)
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No battery estimate yet")
    return estimate


@router.get("/{vehicle_id}/drives", response_model=list[DriveSessionOut])
async def list_drives(
    vehicle_id: uuid.UUID,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[DriveSessionOut]:
    """Derive drive sessions from snapshot windows where speed > 0 or odometer advances."""
    since = datetime.now(timezone.utc) - timedelta(days=min(days, 365))
    result = await db.execute(
        select(VehicleSnapshot)
        .where(
            VehicleSnapshot.vehicle_id == vehicle_id,
            VehicleSnapshot.observed_at >= since,
        )
        .order_by(VehicleSnapshot.observed_at)
    )
    snaps = list(result.scalars().all())
    return _derive_drives(snaps)


def _derive_drives(snaps: list[VehicleSnapshot]) -> list[DriveSessionOut]:
    """
    Derive drive sessions from snapshot stream.
    A drive starts when speed > 0 or shift_state != null, ends when idle for > 5 min.
    Uses odometer delta for distance, SoC delta × nominal_kwh for energy.
    """
    drives: list[DriveSessionOut] = []
    if not snaps:
        return drives

    in_drive = False
    drive_start_idx = 0

    for i, snap in enumerate(snaps):
        moving = (snap.speed_kmh is not None and snap.speed_kmh > 2.0) or (
            snap.vehicle_state == "driving"
        )

        if not in_drive and moving:
            in_drive = True
            drive_start_idx = i

        elif in_drive and not moving:
            # Check if gap is > 5 min before declaring drive over
            if i + 1 < len(snaps):
                gap = (snaps[i + 1].observed_at - snap.observed_at).total_seconds()
                if gap < 300:
                    continue

            drive_snaps = snaps[drive_start_idx:i + 1]
            drive = _build_drive(drive_snaps)
            if drive:
                drives.append(drive)
            in_drive = False

    # Catch open drive at end of window
    if in_drive:
        drive_snaps = snaps[drive_start_idx:]
        drive = _build_drive(drive_snaps)
        if drive:
            drives.append(drive)

    return list(reversed(drives))


def _build_drive(snaps: list[VehicleSnapshot]) -> DriveSessionOut | None:
    if len(snaps) < 2:
        return None

    start, end = snaps[0], snaps[-1]
    duration_min = (end.observed_at - start.observed_at).total_seconds() / 60

    if duration_min < 1:
        return None

    # Distance from odometer delta
    distance_km: float | None = None
    if start.odometer_km is not None and end.odometer_km is not None:
        distance_km = round(float(end.odometer_km) - float(start.odometer_km), 2)
        if distance_km < 0:
            distance_km = None

    # Energy from SoC delta (rough — improved when battery estimate exists)
    energy_kwh: float | None = None
    start_soc = float(start.usable_battery_level or start.battery_level or 0)
    end_soc = float(end.usable_battery_level or end.battery_level or 0)
    soc_delta = start_soc - end_soc  # positive = energy used

    # Efficiency
    efficiency: float | None = None
    if distance_km and distance_km > 0 and energy_kwh:
        efficiency = round(energy_kwh * 1000 / distance_km, 1)

    max_speed = max(
        (float(s.speed_kmh) for s in snaps if s.speed_kmh is not None), default=None
    )

    return DriveSessionOut(
        started_at=start.observed_at,
        ended_at=end.observed_at,
        distance_km=distance_km,
        energy_kwh=energy_kwh,
        efficiency_wh_per_km=efficiency,
        start_soc=round(start_soc, 1) if start_soc else None,
        end_soc=round(end_soc, 1) if end_soc else None,
        max_speed_kmh=round(max_speed, 1) if max_speed else None,
        duration_minutes=round(duration_min, 1),
    )
