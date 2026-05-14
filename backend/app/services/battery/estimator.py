"""
Battery health estimator.

Given a list of ChargeSession records, infers the vehicle's usable battery
capacity by treating each session as a measurement of the full-pack size:

    inferred_kwh = battery_kwh_added / ((end_soc - start_soc) / 100)

The median of all qualifying inferences is used as the estimated usable
capacity, which is robust to outliers from partial charges.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from app.models.charge import ChargeSession

# Plausible capacity range for any modern EV (kWh)
_MIN_INFERRED_KWH = 30.0
_MAX_INFERRED_KWH = 120.0

# Minimum SOC delta to avoid amplifying measurement noise
_MIN_SOC_DELTA = 5.0


@dataclass
class EstimatorResult:
    estimated_usable_kwh: float
    degradation_pct: float | None
    confidence: str  # unknown / low / moderate / high
    sessions_used: int
    explanation: list[str] = field(default_factory=list)


def estimate_battery(
    sessions: list[ChargeSession],
    nominal_kwh: float,
) -> EstimatorResult:
    """Estimate usable battery capacity from charge session history.

    Args:
        sessions:    All available ChargeSession records for the vehicle.
        nominal_kwh: The nameplate (rated) usable capacity for this pack.

    Returns:
        An EstimatorResult.  When fewer than 3 qualifying sessions exist the
        result still returns an estimate but with confidence="unknown".
    """
    inferences: list[float] = []
    skipped_missing = 0
    skipped_invalid = 0
    skipped_tiny_delta = 0
    skipped_out_of_range = 0

    for s in sessions:
        # Must have energy added and both SOC endpoints
        if s.battery_kwh_added is None or s.start_soc is None or s.end_soc is None:
            skipped_missing += 1
            continue

        # Discard flagged sessions
        if s.invalid:
            skipped_invalid += 1
            continue

        kwh_added = float(s.battery_kwh_added)
        soc_delta = float(s.end_soc) - float(s.start_soc)

        if kwh_added <= 0:
            skipped_missing += 1
            continue

        # Require a meaningful SOC swing to keep noise small
        if soc_delta < _MIN_SOC_DELTA:
            skipped_tiny_delta += 1
            continue

        inferred = kwh_added / (soc_delta / 100.0)

        # Reject physically implausible values
        if inferred < _MIN_INFERRED_KWH or inferred > _MAX_INFERRED_KWH:
            skipped_out_of_range += 1
            continue

        inferences.append(inferred)

    explanation: list[str] = []

    if skipped_missing:
        explanation.append(
            f"{skipped_missing} session(s) skipped: missing energy or SOC data."
        )
    if skipped_invalid:
        explanation.append(f"{skipped_invalid} session(s) skipped: marked invalid.")
    if skipped_tiny_delta:
        explanation.append(
            f"{skipped_tiny_delta} session(s) skipped: SOC delta < {_MIN_SOC_DELTA}%."
        )
    if skipped_out_of_range:
        explanation.append(
            f"{skipped_out_of_range} session(s) skipped: inferred capacity outside "
            f"{_MIN_INFERRED_KWH}–{_MAX_INFERRED_KWH} kWh range."
        )

    n = len(inferences)

    if n == 0:
        # No usable data — return nominal as placeholder with unknown confidence
        explanation.append(
            "No qualifying sessions found; returning nominal capacity as placeholder."
        )
        return EstimatorResult(
            estimated_usable_kwh=nominal_kwh,
            degradation_pct=0.0,
            confidence="unknown",
            sessions_used=0,
            explanation=explanation,
        )

    estimated = statistics.median(inferences)

    # Confidence bands
    if n < 3:
        confidence = "unknown"
    elif n < 10:
        confidence = "low"
    elif n < 25:
        confidence = "moderate"
    else:
        confidence = "high"

    degradation_pct = (nominal_kwh - estimated) / nominal_kwh * 100.0

    spread = max(inferences) - min(inferences)
    explanation.append(
        f"Estimated from {n} qualifying session(s). "
        f"Median inferred capacity: {estimated:.1f} kWh "
        f"(spread {spread:.1f} kWh across qualifying sessions)."
    )
    explanation.append(
        f"Nominal capacity: {nominal_kwh:.1f} kWh → "
        f"estimated degradation: {degradation_pct:.1f}%."
    )
    explanation.append(f"Confidence: {confidence}.")

    return EstimatorResult(
        estimated_usable_kwh=round(estimated, 3),
        degradation_pct=round(degradation_pct, 2),
        confidence=confidence,
        sessions_used=n,
        explanation=explanation,
    )
