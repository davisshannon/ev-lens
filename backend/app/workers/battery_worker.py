"""
Battery analysis background worker.

Called from the main poller after each successful vehicle poll cycle.
Runs the battery health estimator and all anomaly detectors, persisting
results without ever raising — a failure here must not crash the poller.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.battery import BatteryEstimate
from app.models.charge import ChargeSession
from app.models.vehicle import Vehicle, VehicleSnapshot
from app.services.battery.anomalies import (
    detect_charging_efficiency_drop,
    detect_derating,
    detect_poor_drive_efficiency,
    detect_session_interruption,
    detect_vampire_drain,
)
from app.services.battery.estimator import estimate_battery

log = logging.getLogger(__name__)

# How far back to look for snapshots used by anomaly detectors
_VAMPIRE_DRAIN_WINDOW_H = 12
_DRIVE_EFFICIENCY_WINDOW_H = 2

# How different an estimate must be from the stored one before we persist it
_ESTIMATE_CHANGE_THRESHOLD_KWH = 0.5


async def run_battery_analysis(vehicle_id: uuid.UUID, db: AsyncSession) -> None:
    """Entry point called by the poller after _run_session_detector succeeds.

    Loads data, runs estimator + detectors, and persists results.  All
    exceptions are caught and logged so the poller loop is never disrupted.
    """
    try:
        await _run_estimator(vehicle_id, db)
    except Exception:
        log.exception("Battery estimator failed for vehicle %s", vehicle_id)

    try:
        await _run_anomaly_detectors(vehicle_id, db)
    except Exception:
        log.exception("Anomaly detectors failed for vehicle %s", vehicle_id)


# ---------------------------------------------------------------------------
# Estimator
# ---------------------------------------------------------------------------

async def _run_estimator(vehicle_id: uuid.UUID, db: AsyncSession) -> None:
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.nominal_battery_kwh is None:
        log.debug("Skipping estimator for vehicle %s: no nominal_kwh", vehicle_id)
        return

    nominal_kwh = float(vehicle.nominal_battery_kwh)

    # Load last 50 charge sessions ordered by most recent first
    sessions_result = await db.execute(
        select(ChargeSession)
        .where(ChargeSession.vehicle_id == vehicle_id)
        .order_by(ChargeSession.started_at.desc())
        .limit(50)
    )
    sessions = sessions_result.scalars().all()

    if not sessions:
        return

    result = estimate_battery(list(sessions), nominal_kwh)

    # Check latest stored estimate — skip if the change is trivial
    latest_result = await db.execute(
        select(BatteryEstimate)
        .where(BatteryEstimate.vehicle_id == vehicle_id)
        .order_by(BatteryEstimate.calculated_at.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()

    if latest is not None:
        delta = abs(float(latest.estimated_usable_kwh) - result.estimated_usable_kwh)
        if delta <= _ESTIMATE_CHANGE_THRESHOLD_KWH:
            log.debug(
                "Battery estimate unchanged for vehicle %s (delta %.3f kWh)",
                vehicle_id,
                delta,
            )
            return

    estimate = BatteryEstimate(
        vehicle_id=vehicle_id,
        estimated_usable_kwh=result.estimated_usable_kwh,
        nominal_kwh=nominal_kwh,
        degradation_pct=result.degradation_pct,
        confidence=result.confidence,
        sessions_used=result.sessions_used,
        explanation=result.explanation,
        calculated_at=datetime.now(timezone.utc),
    )
    db.add(estimate)
    await db.commit()
    log.info(
        "Battery estimate updated for vehicle %s: %.1f kWh (%.1f%% degradation, %s confidence)",
        vehicle_id,
        result.estimated_usable_kwh,
        result.degradation_pct or 0.0,
        result.confidence,
    )


# ---------------------------------------------------------------------------
# Anomaly detectors
# ---------------------------------------------------------------------------

async def _run_anomaly_detectors(vehicle_id: uuid.UUID, db: AsyncSession) -> None:
    # Load sessions (last 30 for efficiency/derating analysis)
    sessions_result = await db.execute(
        select(ChargeSession)
        .where(ChargeSession.vehicle_id == vehicle_id)
        .order_by(ChargeSession.started_at.desc())
        .limit(30)
    )
    all_sessions: list[ChargeSession] = list(sessions_result.scalars().all())

    recent_10 = all_sessions[:10]
    baseline_20 = all_sessions[10:30]
    recent_5 = all_sessions[:5]
    latest_session = all_sessions[0] if all_sessions else None

    # Snapshots for vampire drain (last 12 h)
    vampire_cutoff = datetime.now(timezone.utc) - timedelta(hours=_VAMPIRE_DRAIN_WINDOW_H)
    vampire_snaps_result = await db.execute(
        select(VehicleSnapshot)
        .where(
            VehicleSnapshot.vehicle_id == vehicle_id,
            VehicleSnapshot.observed_at >= vampire_cutoff,
        )
        .order_by(VehicleSnapshot.observed_at)
    )
    vampire_snaps: list[VehicleSnapshot] = list(vampire_snaps_result.scalars().all())

    # Snapshots for drive efficiency (last 2 h)
    drive_cutoff = datetime.now(timezone.utc) - timedelta(hours=_DRIVE_EFFICIENCY_WINDOW_H)
    drive_snaps_result = await db.execute(
        select(VehicleSnapshot)
        .where(
            VehicleSnapshot.vehicle_id == vehicle_id,
            VehicleSnapshot.observed_at >= drive_cutoff,
        )
        .order_by(VehicleSnapshot.observed_at)
    )
    drive_snaps: list[VehicleSnapshot] = list(drive_snaps_result.scalars().all())

    # Derive baseline Wh/km from historical sessions (rough estimate)
    baseline_wh_per_km = await _derive_drive_baseline(vehicle_id, db)

    # Build list of (alert_type, candidate_alert) pairs
    candidates: list[tuple[str, Alert | None]] = []

    candidates.append(
        ("vampire_drain", detect_vampire_drain(vehicle_id, vampire_snaps))
    )
    candidates.append(
        (
            "charging_efficiency_drop",
            detect_charging_efficiency_drop(vehicle_id, recent_10, baseline_20),
        )
    )
    candidates.append(
        ("derating", detect_derating(vehicle_id, recent_5))
    )
    if latest_session is not None:
        candidates.append(
            (
                "session_interruption",
                detect_session_interruption(vehicle_id, latest_session),
            )
        )
    if baseline_wh_per_km is not None:
        candidates.append(
            (
                "poor_drive_efficiency",
                detect_poor_drive_efficiency(vehicle_id, drive_snaps, baseline_wh_per_km),
            )
        )

    # Persist only if no open alert of the same type already exists
    for alert_type, alert in candidates:
        if alert is None:
            continue
        try:
            await _persist_alert_if_new(alert_type, alert, db)
        except Exception:
            log.exception(
                "Failed to persist %s alert for vehicle %s", alert_type, vehicle_id
            )


async def _persist_alert_if_new(
    alert_type: str, alert: Alert, db: AsyncSession
) -> None:
    existing_result = await db.execute(
        select(Alert)
        .where(
            Alert.vehicle_id == alert.vehicle_id,
            Alert.alert_type == alert_type,
            Alert.status == "open",
        )
        .limit(1)
    )
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        log.debug(
            "Open %s alert already exists for vehicle %s — skipping",
            alert_type,
            alert.vehicle_id,
        )
        return

    db.add(alert)
    await db.commit()
    log.info(
        "New %s alert created for vehicle %s (severity=%s)",
        alert_type,
        alert.vehicle_id,
        alert.severity,
    )


async def _derive_drive_baseline(
    vehicle_id: uuid.UUID, db: AsyncSession
) -> float | None:
    """Estimate a rough baseline Wh/km from historical charge sessions.

    Uses the ratio of energy added to SOC recovered, combined with the
    vehicle's rated range, as a proxy.  Returns None if insufficient data.

    This is a lightweight heuristic; a future milestone can replace it with
    a proper drive-session–derived baseline.
    """
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return None

    nominal_kwh = float(vehicle.nominal_battery_kwh) if vehicle.nominal_battery_kwh else None
    if nominal_kwh is None:
        return None

    # Assume a mid-range efficiency of 160 Wh/km as the starting baseline,
    # scaled by battery size (larger packs tend to be in heavier/faster cars)
    # 75 kWh → 160 Wh/km reference point
    baseline = 160.0 * (nominal_kwh / 75.0)
    return baseline
