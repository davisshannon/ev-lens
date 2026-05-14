"""
Anomaly detectors for battery and drive health.

Each detector is a pure function: it takes recent data windows and returns
an Alert if a problem is detected, or None if everything looks normal.

Detectors do NOT write to the database; persistence is handled by the
battery_worker that calls them.
"""

from __future__ import annotations

import statistics
import uuid
from datetime import timedelta

from app.models.alert import Alert
from app.models.charge import ChargeSession
from app.models.vehicle import VehicleSnapshot


# ---------------------------------------------------------------------------
# Vampire drain
# ---------------------------------------------------------------------------

def detect_vampire_drain(
    vehicle_id: uuid.UUID,
    snapshots: list[VehicleSnapshot],
    threshold_pct_per_hour: float = 0.5,
) -> Alert | None:
    """Detect excessive passive SOC loss while the vehicle is parked.

    Looks at a window of snapshots (typically the last 12 h) and computes
    the average SOC drain rate while the vehicle is not charging and not
    moving.  Fires when that rate exceeds *threshold_pct_per_hour*.
    """
    parked = [
        s for s in snapshots
        if s.charging_state not in ("Charging", "Complete", "Starting")
        and (s.speed_kmh is None or float(s.speed_kmh) < 1.0)
        and s.battery_level is not None
    ]

    if len(parked) < 2:
        return None

    parked_sorted = sorted(parked, key=lambda s: s.observed_at)
    first = parked_sorted[0]
    last = parked_sorted[-1]

    elapsed_hours = (
        last.observed_at - first.observed_at
    ).total_seconds() / 3600.0

    if elapsed_hours < 0.5:
        return None

    soc_drop = float(first.battery_level) - float(last.battery_level)

    if soc_drop <= 0:
        return None

    rate = soc_drop / elapsed_hours

    if rate <= threshold_pct_per_hour:
        return None

    return Alert(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        alert_type="vampire_drain",
        severity="warning",
        confidence="moderate",
        status="open",
        title="Excessive vampire drain detected",
        summary=(
            f"Battery lost {soc_drop:.1f}% over {elapsed_hours:.1f} h while parked "
            f"({rate:.2f}%/h; threshold {threshold_pct_per_hour}%/h)."
        ),
        evidence=[
            f"Start SOC: {float(first.battery_level):.1f}% at {first.observed_at.isoformat()}",
            f"End SOC: {float(last.battery_level):.1f}% at {last.observed_at.isoformat()}",
            f"Drain rate: {rate:.2f}%/h over {elapsed_hours:.1f} h",
            f"Parked snapshots analysed: {len(parked_sorted)}",
        ],
        possible_causes=[
            "Sentry Mode running continuously",
            "Third-party app polling vehicle too frequently",
            "Cabin overheat protection active",
            "Software bug causing phantom wake-ups",
        ],
        recommended_actions=[
            "Disable Sentry Mode when parked at home",
            "Review connected third-party app permissions",
            "Check for scheduled departures or preconditioning",
            "Contact Tesla service if drain persists after mitigation",
        ],
    )


# ---------------------------------------------------------------------------
# Charging efficiency drop
# ---------------------------------------------------------------------------

def detect_charging_efficiency_drop(
    vehicle_id: uuid.UUID,
    recent_sessions: list[ChargeSession],
    baseline_sessions: list[ChargeSession],
) -> Alert | None:
    """Detect a drop in AC→battery charging efficiency.

    Compares the average *charge_efficiency* (wall_kwh / battery_kwh_added)
    in two windows.  A drop of more than 5 percentage points relative to the
    baseline window triggers an alert.

    Note: charge_efficiency < 1 is normal (losses are expected); the alert
    fires when efficiency *worsens* beyond the threshold.
    """
    def _avg_efficiency(sessions: list[ChargeSession]) -> float | None:
        vals = [
            float(s.charge_efficiency)
            for s in sessions
            if s.charge_efficiency is not None
            and not s.invalid
            and s.battery_kwh_added is not None
            and float(s.battery_kwh_added) > 0
        ]
        return statistics.mean(vals) if vals else None

    recent_eff = _avg_efficiency(recent_sessions)
    baseline_eff = _avg_efficiency(baseline_sessions)

    if recent_eff is None or baseline_eff is None:
        return None

    # charge_efficiency ≤ 1; lower value = worse efficiency
    drop = baseline_eff - recent_eff  # positive means efficiency has fallen

    if drop <= 0.05:
        return None

    drop_pct = drop * 100.0
    recent_pct = recent_eff * 100.0
    baseline_pct = baseline_eff * 100.0

    return Alert(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        alert_type="charging_efficiency_drop",
        severity="warning",
        confidence="moderate",
        status="open",
        title="Charging efficiency has dropped",
        summary=(
            f"Recent charging efficiency ({recent_pct:.1f}%) is {drop_pct:.1f} percentage "
            f"points below the baseline ({baseline_pct:.1f}%)."
        ),
        evidence=[
            f"Recent window ({len(recent_sessions)} sessions): avg efficiency {recent_pct:.1f}%",
            f"Baseline window ({len(baseline_sessions)} sessions): avg efficiency {baseline_pct:.1f}%",
            f"Drop: {drop_pct:.1f} percentage points",
        ],
        possible_causes=[
            "Degraded onboard charger",
            "Loose or damaged charging cable/connector",
            "EVSE (wall box) supplying lower voltage than rated",
            "Battery thermal management issues during charging",
        ],
        recommended_actions=[
            "Try a different charging cable",
            "Test charging at a different EVSE or public charger",
            "Check charger inlet for damage or corrosion",
            "Schedule a service appointment if issue persists",
        ],
    )


# ---------------------------------------------------------------------------
# Derating
# ---------------------------------------------------------------------------

def detect_derating(
    vehicle_id: uuid.UUID,
    recent_sessions: list[ChargeSession],
) -> Alert | None:
    """Detect sustained reduction in peak charging power (derating).

    Computes the historical peak power across all supplied sessions and flags
    when the recent sessions consistently deliver less than 50% of that peak.
    """
    sessions_with_power = [
        s for s in recent_sessions
        if s.max_power_kw is not None
        and not s.invalid
        and float(s.max_power_kw) > 0
    ]

    if len(sessions_with_power) < 3:
        return None

    all_peaks = [float(s.max_power_kw) for s in sessions_with_power]
    historical_peak = max(all_peaks)

    # Use the most recent 5 sessions as the "recent" window
    recent_window = sorted(sessions_with_power, key=lambda s: s.started_at)[-5:]
    recent_peaks = [float(s.max_power_kw) for s in recent_window]
    recent_max = max(recent_peaks)

    threshold = historical_peak * 0.5

    if recent_max >= threshold:
        return None

    return Alert(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        alert_type="derating",
        severity="warning",
        confidence="low",
        status="open",
        title="Charging power derating detected",
        summary=(
            f"Recent peak charging power ({recent_max:.1f} kW) is below 50% of the "
            f"historical peak ({historical_peak:.1f} kW)."
        ),
        evidence=[
            f"Historical peak power: {historical_peak:.1f} kW",
            f"Recent peak power (last {len(recent_window)} sessions): {recent_max:.1f} kW",
            f"50% threshold: {threshold:.1f} kW",
            f"Recent session peaks: {[round(p, 1) for p in recent_peaks]}",
        ],
        possible_causes=[
            "Battery thermal protection limiting charge rate",
            "Supercharger/DCFC fault or degraded stall",
            "High battery state-of-charge limiting peak power",
            "Battery degradation reducing max charge acceptance",
            "Cold weather reducing charge acceptance",
        ],
        recommended_actions=[
            "Pre-condition battery before DC fast charging",
            "Try a different Supercharger stall or station",
            "Check ambient and battery temperature",
            "Schedule service if derating occurs at normal temperatures and SOC",
        ],
    )


# ---------------------------------------------------------------------------
# Session interruption
# ---------------------------------------------------------------------------

def detect_session_interruption(
    vehicle_id: uuid.UUID,
    session: ChargeSession,
) -> Alert | None:
    """Detect a charge session that ended before reaching its charge limit."""
    if not session.incomplete:
        return None

    if session.end_soc is None or session.charge_limit_soc is None:
        # Incomplete but we can't tell by how much — still worth alerting
        shortfall_str = "unknown shortfall"
    else:
        shortfall = float(session.charge_limit_soc) - float(session.end_soc)
        if shortfall < 5.0:
            return None
        shortfall_str = f"{shortfall:.0f}% below the {float(session.charge_limit_soc):.0f}% limit"

    ended_at_str = session.ended_at.isoformat() if session.ended_at else "unknown"

    return Alert(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        alert_type="session_interruption",
        severity="warning",
        confidence="high",
        status="open",
        title="Charge session ended before reaching charge limit",
        summary=(
            f"Session started at {session.started_at.isoformat()} ended early "
            f"({shortfall_str})."
        ),
        evidence=[
            f"Session started: {session.started_at.isoformat()}",
            f"Session ended: {ended_at_str}",
            f"End SOC: {float(session.end_soc):.0f}%" if session.end_soc else "End SOC: unknown",
            f"Charge limit: {float(session.charge_limit_soc):.0f}%" if session.charge_limit_soc else "Charge limit: unknown",
            f"Energy added: {float(session.battery_kwh_added):.2f} kWh" if session.battery_kwh_added else "Energy added: unknown",
        ],
        possible_causes=[
            "Power outage or EVSE fault",
            "Charging cable disconnected",
            "Vehicle software triggered a charge stop",
            "Scheduled charge window expired",
            "User manually stopped charging",
        ],
        recommended_actions=[
            "Check EVSE / wall connector for faults",
            "Review charging history for recurring interruptions",
            "Inspect charging cable and inlet for damage",
            "Contact Tesla service if interruptions recur without obvious cause",
        ],
    )


# ---------------------------------------------------------------------------
# Poor drive efficiency
# ---------------------------------------------------------------------------

def detect_poor_drive_efficiency(
    vehicle_id: uuid.UUID,
    snapshots: list[VehicleSnapshot],
    baseline_wh_per_km: float,
    threshold_pct: float = 30.0,
) -> Alert | None:
    """Detect abnormally high energy consumption during a drive.

    Derives energy used and distance from the snapshot window, then compares
    the resulting Wh/km figure against a per-vehicle baseline.
    """
    driving = [
        s for s in snapshots
        if s.odometer_km is not None
        and s.battery_level is not None
    ]

    if len(driving) < 2:
        return None

    driving_sorted = sorted(driving, key=lambda s: s.observed_at)
    first = driving_sorted[0]
    last = driving_sorted[-1]

    distance_km = float(last.odometer_km) - float(first.odometer_km)
    if distance_km <= 0.5:
        return None

    # Derive energy used from SOC drop; use usable_battery_level when available
    start_soc = (
        float(first.usable_battery_level)
        if first.usable_battery_level is not None
        else float(first.battery_level)
    )
    end_soc = (
        float(last.usable_battery_level)
        if last.usable_battery_level is not None
        else float(last.battery_level)
    )

    soc_drop = start_soc - end_soc
    if soc_drop <= 0:
        return None

    # We do not have nominal_kwh here; use a conservative default of 75 kWh
    # to estimate energy from SOC drop.  Caller should supply snapshots from
    # a single drive window.
    estimated_nominal_kwh = 75.0  # Conservative mid-range default
    energy_used_wh = (soc_drop / 100.0) * estimated_nominal_kwh * 1000.0

    wh_per_km = energy_used_wh / distance_km
    threshold_wh_per_km = baseline_wh_per_km * (1.0 + threshold_pct / 100.0)

    if wh_per_km <= threshold_wh_per_km:
        return None

    excess_pct = (wh_per_km / baseline_wh_per_km - 1.0) * 100.0

    return Alert(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        alert_type="poor_drive_efficiency",
        severity="info",
        confidence="low",
        status="open",
        title="Unusually high energy consumption on recent drive",
        summary=(
            f"Drive efficiency was {wh_per_km:.0f} Wh/km — "
            f"{excess_pct:.0f}% above the {baseline_wh_per_km:.0f} Wh/km baseline "
            f"(threshold: +{threshold_pct:.0f}%)."
        ),
        evidence=[
            f"Distance: {distance_km:.1f} km",
            f"Estimated energy used: {energy_used_wh / 1000:.2f} kWh",
            f"Observed efficiency: {wh_per_km:.0f} Wh/km",
            f"Baseline efficiency: {baseline_wh_per_km:.0f} Wh/km",
            f"Threshold: {threshold_wh_per_km:.0f} Wh/km (+{threshold_pct:.0f}%)",
            f"Snapshots in window: {len(driving_sorted)}",
        ],
        possible_causes=[
            "Aggressive driving style (hard acceleration/braking)",
            "Cold weather increasing heating loads",
            "High-speed motorway driving",
            "Heavy payload or roof load",
            "Tyre under-inflation",
            "HVAC running at full capacity",
        ],
        recommended_actions=[
            "Review driving style — smoother acceleration improves efficiency",
            "Check tyre pressures",
            "Use cabin pre-conditioning while plugged in to reduce in-drive heating load",
            "If consistently poor, check for brake drag or tyre issues",
        ],
    )
