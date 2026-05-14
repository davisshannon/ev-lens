import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.db import get_db
from app.models.tariff import Tariff, VehicleTariffAssignment
from app.schemas.charge import TariffIn, TariffOut

router = APIRouter()


@router.get("", response_model=list[TariffOut])
async def list_tariffs(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[Tariff]:
    result = await db.execute(select(Tariff).order_by(Tariff.name))
    return list(result.scalars().all())


@router.post("", response_model=TariffOut, status_code=status.HTTP_201_CREATED)
async def create_tariff(
    body: TariffIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> Tariff:
    tariff = Tariff(
        id=uuid.uuid4(),
        name=body.name,
        currency=body.currency,
        timezone=body.timezone,
        config=body.config,
    )
    db.add(tariff)
    await db.commit()
    await db.refresh(tariff)
    return tariff


@router.put("/{tariff_id}", response_model=TariffOut)
async def update_tariff(
    tariff_id: uuid.UUID,
    body: TariffIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> Tariff:
    result = await db.execute(select(Tariff).where(Tariff.id == tariff_id))
    tariff = result.scalar_one_or_none()
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")
    tariff.name = body.name
    tariff.currency = body.currency
    tariff.timezone = body.timezone
    tariff.config = body.config
    await db.commit()
    await db.refresh(tariff)
    return tariff


@router.delete("/{tariff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tariff(
    tariff_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> None:
    result = await db.execute(select(Tariff).where(Tariff.id == tariff_id))
    tariff = result.scalar_one_or_none()
    if not tariff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")
    await db.delete(tariff)
    await db.commit()


@router.post("/{tariff_id}/assign/{vehicle_id}", status_code=status.HTTP_201_CREATED)
async def assign_tariff_to_vehicle(
    tariff_id: uuid.UUID,
    vehicle_id: uuid.UUID,
    set_default: bool = True,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> dict:
    assignment = VehicleTariffAssignment(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        tariff_id=tariff_id,
        is_default=set_default,
    )
    db.add(assignment)
    await db.commit()
    return {"status": "assigned"}
