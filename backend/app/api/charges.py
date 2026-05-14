import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.db import get_db
from app.models.charge import ChargePlan, ChargeSession
from app.models.tariff import Tariff, VehicleTariffAssignment
from app.models.vehicle import Vehicle
from app.schemas.battery import CostSummaryOut
from app.schemas.charge import ChargePlanOut, ChargePlanRequest, ChargeSessionOut, PostChargeReportOut
from app.services.charging.planner import PlanInput, build_post_charge_report, plan_charge

router = APIRouter()


@router.get("/{vehicle_id}/sessions", response_model=list[ChargeSessionOut])
async def list_sessions(
    vehicle_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[ChargeSession]:
    result = await db.execute(
        select(ChargeSession)
        .where(ChargeSession.vehicle_id == vehicle_id, ChargeSession.invalid.is_(False))
        .order_by(ChargeSession.started_at.desc())
        .limit(min(limit, 200))
    )
    return list(result.scalars().all())


@router.get("/{vehicle_id}/sessions/{session_id}", response_model=ChargeSessionOut)
async def get_session(
    vehicle_id: uuid.UUID,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> ChargeSession:
    result = await db.execute(
        select(ChargeSession).where(
            ChargeSession.id == session_id,
            ChargeSession.vehicle_id == vehicle_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.post("/{vehicle_id}/plan", response_model=ChargePlanOut)
async def create_charge_plan(
    vehicle_id: uuid.UUID,
    body: ChargePlanRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> ChargePlan:
    vehicle = await _get_vehicle(vehicle_id, db)
    tariff, tariff_id = await _resolve_tariff(vehicle_id, body.tariff_id, db)

    if tariff is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No tariff configured. Add a tariff in Settings first.",
        )

    nominal_kwh = float(vehicle.nominal_battery_kwh or 75.0)
    inputs = PlanInput(
        vehicle_id=vehicle_id,
        current_soc=body.current_soc,
        target_soc=body.target_soc,
        nominal_kwh=nominal_kwh,
        tariff_config=tariff.config,
        tariff_tz=tariff.timezone,
        tariff_id=tariff_id,
        departure_time=body.departure_time,
    )
    result = plan_charge(inputs)

    plan = ChargePlan(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        tariff_id=tariff_id,
        current_soc=body.current_soc,
        target_soc=body.target_soc,
        departure_time=body.departure_time,
        recommended_start=result.recommended_start,
        recommended_stop=result.recommended_stop,
        expected_kwh=result.expected_kwh,
        expected_cost=result.expected_cost,
        expected_cost_currency=tariff.currency,
        confidence=result.confidence,
        explanation=result.explanation,
        inputs={"rate_at_start": result.rate_at_start, "window": result.window_name},
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.get("/{vehicle_id}/plans", response_model=list[ChargePlanOut])
async def list_plans(
    vehicle_id: uuid.UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[ChargePlan]:
    result = await db.execute(
        select(ChargePlan)
        .where(ChargePlan.vehicle_id == vehicle_id)
        .order_by(ChargePlan.created_at.desc())
        .limit(min(limit, 100))
    )
    return list(result.scalars().all())


@router.get("/{vehicle_id}/plans/{plan_id}/report", response_model=PostChargeReportOut)
async def get_post_charge_report(
    vehicle_id: uuid.UUID,
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> dict:
    result = await db.execute(
        select(ChargePlan).where(ChargePlan.id == plan_id, ChargePlan.vehicle_id == vehicle_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if plan.actual_kwh is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No post-charge data yet — session may still be in progress.",
        )

    return build_post_charge_report(
        plan_expected_kwh=float(plan.expected_kwh or 0),
        plan_expected_cost=float(plan.expected_cost or 0),
        plan_start=plan.recommended_start or plan.created_at,
        actual_start=plan.actual_start or plan.recommended_start or plan.created_at,
        actual_stop=plan.actual_stop or datetime.now(timezone.utc),
        actual_kwh=float(plan.actual_kwh),
        actual_cost=float(plan.actual_cost or 0),
    )


@router.get("/{vehicle_id}/costs", response_model=list[CostSummaryOut])
async def get_cost_summary(
    vehicle_id: uuid.UUID,
    months: int = 6,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[CostSummaryOut]:
    since = datetime.now(timezone.utc) - timedelta(days=min(months, 24) * 31)
    result = await db.execute(
        select(ChargeSession)
        .where(
            ChargeSession.vehicle_id == vehicle_id,
            ChargeSession.invalid.is_(False),
            ChargeSession.started_at >= since,
        )
        .order_by(ChargeSession.started_at)
    )
    sessions = list(result.scalars().all())

    # Group by YYYY-MM
    by_month: dict[str, list[ChargeSession]] = defaultdict(list)
    for s in sessions:
        key = s.started_at.strftime("%Y-%m")
        by_month[key].append(s)

    summaries: list[CostSummaryOut] = []
    for period in sorted(by_month.keys()):
        month_sessions = by_month[period]
        total_cost = sum(float(s.cost_estimated or 0) for s in month_sessions)
        total_kwh = sum(
            float(s.wall_kwh_actual or s.wall_kwh_estimated or s.battery_kwh_added or 0)
            for s in month_sessions
        )
        solar_kwh = sum(float(s.solar_kwh or 0) for s in month_sessions)
        grid_kwh = sum(float(s.grid_kwh or 0) for s in month_sessions)
        currency = next(
            (s.cost_currency for s in month_sessions if s.cost_currency), "USD"
        )
        summaries.append(
            CostSummaryOut(
                period=period,
                total_cost=round(total_cost, 4),
                total_kwh=round(total_kwh, 3),
                currency=currency,
                session_count=len(month_sessions),
                avg_cost_per_kwh=round(total_cost / total_kwh, 4) if total_kwh > 0 else None,
                avg_cost_per_100km=None,  # requires drive distance correlation
                solar_kwh=round(solar_kwh, 3),
                grid_kwh=round(grid_kwh, 3),
                solar_pct=round(solar_kwh / total_kwh * 100, 1) if total_kwh > 0 else 0.0,
            )
        )
    return summaries


async def _get_vehicle(vehicle_id: uuid.UUID, db: AsyncSession) -> Vehicle:
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


async def _resolve_tariff(
    vehicle_id: uuid.UUID,
    tariff_id: uuid.UUID | None,
    db: AsyncSession,
) -> tuple[Tariff | None, uuid.UUID | None]:
    if tariff_id:
        result = await db.execute(select(Tariff).where(Tariff.id == tariff_id))
        t = result.scalar_one_or_none()
        return t, tariff_id if t else None

    # Find default assignment for this vehicle
    result = await db.execute(
        select(VehicleTariffAssignment)
        .where(
            VehicleTariffAssignment.vehicle_id == vehicle_id,
            VehicleTariffAssignment.is_default.is_(True),
        )
        .order_by(VehicleTariffAssignment.valid_from.desc())
        .limit(1)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        return None, None

    result2 = await db.execute(select(Tariff).where(Tariff.id == assignment.tariff_id))
    t = result2.scalar_one_or_none()
    return t, assignment.tariff_id
