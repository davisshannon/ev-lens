"""
Deterministic charge planner.

Answers: "Given current SoC, target SoC, departure time, and tariff —
what is the cheapest window to charge, and what will it cost?"

No AI. No stochastic optimisation. Pure time-window math.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.services.charging.tariff import cheapest_window, cost_for_kwh, rate_at

DEFAULT_CHARGE_POWER_KW = 7.4   # Typical Level 2 home charger
DEFAULT_CHARGE_EFFICIENCY = 0.88


@dataclass
class PlanInput:
    vehicle_id: uuid.UUID
    current_soc: float         # 0–100
    target_soc: float          # 0–100
    nominal_kwh: float         # vehicle battery capacity
    tariff_config: dict
    tariff_tz: str
    tariff_id: uuid.UUID | None
    departure_time: datetime | None = None
    charge_power_kw: float = DEFAULT_CHARGE_POWER_KW


@dataclass
class PlanResult:
    recommended_start: datetime
    recommended_stop: datetime
    expected_kwh: float
    expected_cost: float
    confidence: str            # low/moderate/high
    explanation: list[str]
    rate_at_start: float
    window_name: str


def plan_charge(inputs: PlanInput) -> PlanResult:
    """
    Strategy:
    1. Calculate kWh needed.
    2. Find cheapest rate window from now until departure (or next 24h).
    3. Schedule charge to end exactly at departure (if given), or at end of cheap window.
    4. Return plan with explanation.
    """
    kwh_needed = _kwh_needed(inputs)
    charge_hours = (kwh_needed / DEFAULT_CHARGE_EFFICIENCY) / inputs.charge_power_kw
    charge_duration = timedelta(hours=charge_hours)

    now = datetime.now(timezone.utc)
    horizon = inputs.departure_time or (now + timedelta(hours=24))

    window = cheapest_window(inputs.tariff_config, inputs.tariff_tz, now)
    explanation: list[str] = []
    confidence = "moderate"

    if window is None:
        # No TOU data — charge now
        recommended_start = now
        recommended_stop = now + charge_duration
        explanation.append("No tariff windows found — charging immediately.")
        confidence = "low"
        rate = rate_at(inputs.tariff_config, now, inputs.tariff_tz).rate
        window_name = "flat"
    else:
        rate = window.rate
        window_name = window.name

        # Build candidate start: latest possible start within cheap window before departure
        window_start_today = _next_window_start(now, window)
        window_end_today = _next_window_end(window_start_today, window)

        # Prefer charging to finish just before departure; otherwise fill the window
        if inputs.departure_time:
            latest_start = inputs.departure_time - charge_duration
            recommended_start = max(window_start_today, min(latest_start, window_end_today - charge_duration))
            explanation.append(
                f"Scheduled to finish charging by {inputs.departure_time.strftime('%H:%M')}."
            )
            confidence = "high"
        else:
            recommended_start = window_start_today
            explanation.append(f"Charging during off-peak window '{window.name}'.")
            confidence = "moderate"

        recommended_stop = recommended_start + charge_duration

        if recommended_start < now:
            recommended_start = now
            recommended_stop = now + charge_duration
            explanation.append("Cheap window already started — charging now.")

    cost = cost_for_kwh(inputs.tariff_config, kwh_needed, recommended_start, inputs.tariff_tz)

    explanation.append(
        f"Need {kwh_needed:.1f} kWh to go from {inputs.current_soc:.0f}% → {inputs.target_soc:.0f}%."
    )
    explanation.append(
        f"Estimated cost: {inputs.tariff_config.get('currency', '$')}{cost:.2f} "
        f"at {rate:.3f}/kWh ({window_name})."
    )

    return PlanResult(
        recommended_start=recommended_start,
        recommended_stop=recommended_stop,
        expected_kwh=round(kwh_needed, 3),
        expected_cost=round(cost, 4),
        confidence=confidence,
        explanation=explanation,
        rate_at_start=rate,
        window_name=window_name,
    )


def build_post_charge_report(
    plan_expected_kwh: float,
    plan_expected_cost: float,
    plan_start: datetime,
    actual_start: datetime,
    actual_stop: datetime,
    actual_kwh: float,
    actual_cost: float,
) -> dict:
    """Compare plan vs actuals for post-charge report."""
    kwh_delta = round(actual_kwh - plan_expected_kwh, 3)
    cost_delta = round(actual_cost - plan_expected_cost, 4)
    start_offset_min = round((actual_start - plan_start).total_seconds() / 60, 1)

    return {
        "plan_kwh": plan_expected_kwh,
        "actual_kwh": actual_kwh,
        "kwh_delta": kwh_delta,
        "plan_cost": plan_expected_cost,
        "actual_cost": actual_cost,
        "cost_delta": cost_delta,
        "plan_start": plan_start.isoformat(),
        "actual_start": actual_start.isoformat(),
        "start_offset_minutes": start_offset_min,
        "duration_minutes": round((actual_stop - actual_start).total_seconds() / 60, 1),
        "accuracy": "good" if abs(kwh_delta) < 1.0 and abs(cost_delta) < 0.50 else "poor",
    }


def _kwh_needed(inputs: PlanInput) -> float:
    delta_pct = max(0.0, inputs.target_soc - inputs.current_soc)
    return round(inputs.nominal_kwh * (delta_pct / 100.0), 3)


def _next_window_start(now: datetime, window) -> datetime:
    from datetime import time as dtime
    import zoneinfo
    # Find next occurrence of window.start from now
    local_now = now.astimezone(zoneinfo.ZoneInfo(window.name if False else "UTC"))
    today_start = now.replace(
        hour=window.start.hour, minute=window.start.minute, second=0, microsecond=0
    )
    if today_start <= now:
        today_start += timedelta(days=1)
    return today_start


def _next_window_end(start: datetime, window) -> datetime:
    end = start.replace(
        hour=window.end.hour, minute=window.end.minute, second=0, microsecond=0
    )
    if end <= start:
        end += timedelta(days=1)
    return end
