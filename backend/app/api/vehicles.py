from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.vehicle import Vehicle, VehicleSnapshot, ProviderEvent
from app.schemas.vehicle import VehicleOut, SnapshotOut, ProviderHealthOut
from app.api.deps import require_auth

router = APIRouter()


@router.get("", response_model=list[VehicleOut])
async def list_vehicles(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[Vehicle]:
    result = await db.execute(select(Vehicle).order_by(Vehicle.created_at))
    return list(result.scalars().all())


@router.get("/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle(
    vehicle_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> Vehicle:
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


@router.get("/{vehicle_id}/snapshot/latest", response_model=SnapshotOut)
async def get_latest_snapshot(
    vehicle_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> VehicleSnapshot:
    result = await db.execute(
        select(VehicleSnapshot)
        .where(VehicleSnapshot.vehicle_id == vehicle_id)
        .order_by(VehicleSnapshot.observed_at.desc())
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No snapshots yet")
    return snapshot


@router.get("/{vehicle_id}/snapshots", response_model=list[SnapshotOut])
async def get_snapshots(
    vehicle_id: UUID,
    limit: int = 288,  # 24h at 5-min intervals
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[VehicleSnapshot]:
    result = await db.execute(
        select(VehicleSnapshot)
        .where(VehicleSnapshot.vehicle_id == vehicle_id)
        .order_by(VehicleSnapshot.observed_at.desc())
        .limit(min(limit, 2016))  # cap at 1 week
    )
    return list(result.scalars().all())


@router.get("/{vehicle_id}/health", response_model=ProviderHealthOut)
async def get_provider_health(
    vehicle_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> ProviderHealthOut:
    result = await db.execute(
        select(ProviderEvent)
        .where(ProviderEvent.vehicle_id == vehicle_id)
        .order_by(ProviderEvent.occurred_at.desc())
        .limit(20)
    )
    events = result.scalars().all()

    last_success = next((e for e in events if e.event_type == "poll_success"), None)
    recent_errors = sum(1 for e in events if e.severity == "error")
    last_error_event = next((e for e in events if e.severity == "error"), None)

    return ProviderHealthOut(
        healthy=recent_errors < 3,
        last_success_at=last_success.occurred_at if last_success else None,
        last_error=last_error_event.message if last_error_event else None,
        recent_errors=recent_errors,
    )
