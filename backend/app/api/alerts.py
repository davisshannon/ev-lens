import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.db import get_db
from app.models.alert import Alert
from app.schemas.battery import AlertOut

router = APIRouter()


@router.get("/{vehicle_id}", response_model=list[AlertOut])
async def list_alerts(
    vehicle_id: uuid.UUID,
    include_resolved: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[Alert]:
    q = select(Alert).where(Alert.vehicle_id == vehicle_id)
    if not include_resolved:
        q = q.where(Alert.status == "open")
    result = await db.execute(q.order_by(Alert.detected_at.desc()).limit(min(limit, 200)))
    return list(result.scalars().all())


@router.patch("/{vehicle_id}/{alert_id}/dismiss", response_model=AlertOut)
async def dismiss_alert(
    vehicle_id: uuid.UUID,
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> Alert:
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.vehicle_id == vehicle_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.status = "dismissed"
    await db.commit()
    await db.refresh(alert)
    return alert


@router.patch("/{vehicle_id}/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    vehicle_id: uuid.UUID,
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> Alert:
    from datetime import datetime, timezone
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.vehicle_id == vehicle_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert
