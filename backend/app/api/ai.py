import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.db import get_db
from app.models.ai import AiExplanation
from app.models.alert import Alert
from app.models.battery import BatteryEstimate
from app.models.charge import ChargeSession
from app.models.vehicle import VehicleSnapshot
from app.schemas.ai import AiExplainRequest, AiExplanationOut
from app.services.ai.base import ExplanationContext
from app.services.ai.factory import get_ai_provider

router = APIRouter()


@router.post("/explain", response_model=AiExplanationOut)
async def explain(
    body: AiExplainRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> AiExplanation:
    provider = get_ai_provider()
    if provider is None:
        # Persist an error row so the frontend can show a friendly message
        row = AiExplanation(
            id=uuid.uuid4(),
            vehicle_id=body.vehicle_id,
            user_question=body.question,
            error=(
                "No AI provider configured. "
                "Set ANTHROPIC_API_KEY, OPENAI_API_KEY, XAI_API_KEY, "
                "or AWS credentials in your .env file."
            ),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row

    context = await _build_context(body.vehicle_id, body.question_type, db)

    try:
        result = await provider.explain(body.question, context)
        row = AiExplanation(
            id=uuid.uuid4(),
            vehicle_id=body.vehicle_id,
            user_question=body.question,
            context_summary=_summarise_context(context),
            answer_markdown=result.answer_markdown,
            confidence=result.confidence,
            provider=result.provider,
            model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        )
    except Exception as exc:  # noqa: BLE001
        row = AiExplanation(
            id=uuid.uuid4(),
            vehicle_id=body.vehicle_id,
            user_question=body.question,
            error=str(exc),
        )

    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/history/{vehicle_id}", response_model=list[AiExplanationOut])
async def get_history(
    vehicle_id: uuid.UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[AiExplanation]:
    result = await db.execute(
        select(AiExplanation)
        .where(AiExplanation.vehicle_id == vehicle_id)
        .order_by(AiExplanation.asked_at.desc())
        .limit(min(limit, 100))
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Context assembly helpers
# ---------------------------------------------------------------------------

async def _build_context(
    vehicle_id: uuid.UUID,
    question_type: str,
    db: AsyncSession,
) -> ExplanationContext:
    window_hours = 48
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    # Last 5 charge sessions
    charge_result = await db.execute(
        select(ChargeSession)
        .where(
            ChargeSession.vehicle_id == vehicle_id,
            ChargeSession.invalid.is_(False),
        )
        .order_by(ChargeSession.started_at.desc())
        .limit(5)
    )
    sessions = list(charge_result.scalars().all())
    charge_sessions = [_session_to_dict(s) for s in sessions]

    # Latest battery estimate
    battery_result = await db.execute(
        select(BatteryEstimate)
        .where(BatteryEstimate.vehicle_id == vehicle_id)
        .order_by(BatteryEstimate.calculated_at.desc())
        .limit(1)
    )
    latest_estimate = battery_result.scalar_one_or_none()
    battery_estimates = [_battery_to_dict(latest_estimate)] if latest_estimate else []

    # Open alerts
    alerts_result = await db.execute(
        select(Alert)
        .where(Alert.vehicle_id == vehicle_id, Alert.status == "open")
        .order_by(Alert.detected_at.desc())
        .limit(10)
    )
    open_alerts = list(alerts_result.scalars().all())
    alerts = [_alert_to_dict(a) for a in open_alerts]

    # Last 48h snapshots summary (min/max/avg SoC, count)
    snaps_result = await db.execute(
        select(
            func.count(VehicleSnapshot.id).label("count"),
            func.min(VehicleSnapshot.battery_level).label("min_soc"),
            func.max(VehicleSnapshot.battery_level).label("max_soc"),
            func.avg(VehicleSnapshot.battery_level).label("avg_soc"),
            func.min(VehicleSnapshot.outside_temp_c).label("min_temp"),
            func.max(VehicleSnapshot.outside_temp_c).label("max_temp"),
        ).where(
            VehicleSnapshot.vehicle_id == vehicle_id,
            VehicleSnapshot.observed_at >= since,
        )
    )
    row = snaps_result.one()
    snapshots_summary: dict = {
        "snapshot_count": row.count,
        "min_soc_pct": float(row.min_soc) if row.min_soc is not None else None,
        "max_soc_pct": float(row.max_soc) if row.max_soc is not None else None,
        "avg_soc_pct": round(float(row.avg_soc), 1) if row.avg_soc is not None else None,
        "min_outside_temp_c": float(row.min_temp) if row.min_temp is not None else None,
        "max_outside_temp_c": float(row.max_temp) if row.max_temp is not None else None,
        "window_hours": window_hours,
    }

    return ExplanationContext(
        vehicle_id=str(vehicle_id),
        question_type=question_type,
        time_window_hours=window_hours,
        charge_sessions=charge_sessions,
        battery_estimates=battery_estimates,
        alerts=alerts,
        snapshots_summary=snapshots_summary,
    )


def _session_to_dict(s: ChargeSession) -> dict:
    return {
        "id": str(s.id),
        "started_at": s.started_at.isoformat(),
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "start_soc": float(s.start_soc) if s.start_soc is not None else None,
        "end_soc": float(s.end_soc) if s.end_soc is not None else None,
        "charge_limit_soc": float(s.charge_limit_soc) if s.charge_limit_soc is not None else None,
        "battery_kwh_added": float(s.battery_kwh_added) if s.battery_kwh_added is not None else None,
        "wall_kwh_actual": float(s.wall_kwh_actual) if s.wall_kwh_actual is not None else None,
        "wall_kwh_estimated": float(s.wall_kwh_estimated) if s.wall_kwh_estimated is not None else None,
        "avg_power_kw": float(s.avg_power_kw) if s.avg_power_kw is not None else None,
        "max_power_kw": float(s.max_power_kw) if s.max_power_kw is not None else None,
        "charge_efficiency": float(s.charge_efficiency) if s.charge_efficiency is not None else None,
        "cost_estimated": float(s.cost_estimated) if s.cost_estimated is not None else None,
        "cost_currency": s.cost_currency,
        "energy_source": s.energy_source,
        "solar_kwh": float(s.solar_kwh) if s.solar_kwh is not None else None,
        "grid_kwh": float(s.grid_kwh) if s.grid_kwh is not None else None,
        "has_gap": s.has_gap,
        "incomplete": s.incomplete,
    }


def _battery_to_dict(e: BatteryEstimate) -> dict:
    return {
        "calculated_at": e.calculated_at.isoformat(),
        "estimated_usable_kwh": float(e.estimated_usable_kwh),
        "nominal_kwh": float(e.nominal_kwh) if e.nominal_kwh is not None else None,
        "degradation_pct": float(e.degradation_pct) if e.degradation_pct is not None else None,
        "confidence": e.confidence,
        "sessions_used": e.sessions_used,
        "explanation": e.explanation,
    }


def _alert_to_dict(a: Alert) -> dict:
    return {
        "alert_type": a.alert_type,
        "severity": a.severity,
        "confidence": a.confidence,
        "title": a.title,
        "summary": a.summary,
        "detected_at": a.detected_at.isoformat(),
        "evidence": a.evidence,
        "possible_causes": a.possible_causes,
    }


def _summarise_context(ctx: ExplanationContext) -> dict:
    return {
        "question_type": ctx.question_type,
        "time_window_hours": ctx.time_window_hours,
        "charge_session_count": len(ctx.charge_sessions),
        "battery_estimate_count": len(ctx.battery_estimates),
        "alert_count": len(ctx.alerts),
        "has_snapshots_summary": bool(ctx.snapshots_summary),
    }
