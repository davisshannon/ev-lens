"""
Charge session detector.

Implements the state machine defined in docs/charge-session-detection.md.
Idempotent: safe to re-run over the same snapshot window.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.charge import ChargeSession
from app.models.vehicle import VehicleSnapshot

log = logging.getLogger(__name__)

# Configurable thresholds (matches docs/charge-session-detection.md defaults)
COOLDOWN_MINUTES = 15
GAP_THRESHOLD_MINUTES = 15
SPLIT_THRESHOLD_MINUTES = 60
MIN_SESSION_SECONDS = 120
MIN_SESSION_KWH = 0.1
DEFAULT_CHARGE_EFFICIENCY = 0.88


class _State(Enum):
    IDLE = auto()
    PLUGGED_IN = auto()
    CHARGING = auto()
    CHARGING_GAP = auto()
    COMPLETING = auto()


@dataclass
class _Session:
    vehicle_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None = None
    start_soc: float | None = None
    end_soc: float | None = None
    charge_limit_soc: float | None = None
    max_power_kw: float | None = None
    snapshots: list[VehicleSnapshot] = field(default_factory=list)
    has_gap: bool = False
    completing_since: datetime | None = None

    def duration_seconds(self) -> float:
        if self.ended_at is None:
            return 0.0
        return (self.ended_at - self.started_at).total_seconds()

    def kwh_added(self, nominal_kwh: float | None) -> float | None:
        if self.start_soc is None or self.end_soc is None or nominal_kwh is None:
            return None
        delta = self.end_soc - self.start_soc
        if delta <= 0:
            return None
        return round(nominal_kwh * (delta / 100.0), 3)

    def is_valid(self, nominal_kwh: float | None) -> tuple[bool, str | None]:
        if self.duration_seconds() < MIN_SESSION_SECONDS:
            return False, "duration_too_short"
        if self.start_soc is not None and self.end_soc is not None and self.end_soc < self.start_soc:
            return False, "soc_decreased"
        kwh = self.kwh_added(nominal_kwh)
        if kwh is not None and kwh < MIN_SESSION_KWH:
            return False, "energy_below_noise_floor"
        return True, None


async def detect_sessions(
    vehicle_id: uuid.UUID,
    snapshots: Sequence[VehicleSnapshot],
    db: AsyncSession,
    nominal_kwh: float | None = None,
) -> list[ChargeSession]:
    """
    Run the state machine over a sorted snapshot sequence.
    Upserts sessions (deduplicates by vehicle_id + started_at).
    Returns list of sessions created or updated.
    """
    if not snapshots:
        return []

    sorted_snaps = sorted(snapshots, key=lambda s: s.observed_at)
    state = _State.IDLE
    current: _Session | None = None
    results: list[ChargeSession] = []

    for snap in sorted_snaps:
        cs = snap.charging_state or ""
        plugged = snap.plugged_in
        power = snap.charger_power_kw or 0.0

        if state == _State.IDLE:
            if plugged and cs == "Charging":
                state = _State.CHARGING
                current = _new_session(vehicle_id, snap)
            elif plugged:
                state = _State.PLUGGED_IN

        elif state == _State.PLUGGED_IN:
            if cs == "Charging":
                state = _State.CHARGING
                current = _new_session(vehicle_id, snap)
            elif not plugged:
                state = _State.IDLE

        elif state == _State.CHARGING:
            assert current is not None
            current.snapshots.append(snap)
            _update_session(current, snap, power)

            if cs in ("Complete", "Stopped") or not plugged:
                state = _State.COMPLETING
                current.completing_since = snap.observed_at
                current.ended_at = snap.observed_at
                current.end_soc = snap.usable_battery_level or snap.battery_level
            elif _gap_exceeded(current, snap, GAP_THRESHOLD_MINUTES):
                state = _State.CHARGING_GAP
                current.has_gap = True

        elif state == _State.CHARGING_GAP:
            assert current is not None
            if cs == "Charging":
                state = _State.CHARGING
                current.has_gap = True
                _update_session(current, snap, power)
            elif _gap_exceeded(current, snap, SPLIT_THRESHOLD_MINUTES):
                # Gap too long — emit partial session, start fresh if charging
                session = await _emit(current, nominal_kwh, db)
                if session:
                    results.append(session)
                current = None
                state = _State.IDLE
                if cs == "Charging" and plugged:
                    state = _State.CHARGING
                    current = _new_session(vehicle_id, snap)

        elif state == _State.COMPLETING:
            assert current is not None
            if cs == "Charging":
                # Resumed within cooldown — continue session
                state = _State.CHARGING
                current.completing_since = None
                current.ended_at = None
                _update_session(current, snap, power)
            elif current.completing_since and (
                snap.observed_at - current.completing_since
                >= timedelta(minutes=COOLDOWN_MINUTES)
            ):
                session = await _emit(current, nominal_kwh, db)
                if session:
                    results.append(session)
                current = None
                state = _State.IDLE if not plugged else _State.PLUGGED_IN

    # Emit any session still in COMPLETING at end of snapshot window
    if state == _State.COMPLETING and current is not None:
        session = await _emit(current, nominal_kwh, db)
        if session:
            results.append(session)

    return results


def _new_session(vehicle_id: uuid.UUID, snap: VehicleSnapshot) -> _Session:
    return _Session(
        vehicle_id=vehicle_id,
        started_at=snap.observed_at,
        start_soc=snap.usable_battery_level or snap.battery_level,
        charge_limit_soc=snap.charge_limit_soc,
        snapshots=[snap],
    )


def _update_session(session: _Session, snap: VehicleSnapshot, power: float) -> None:
    session.ended_at = snap.observed_at
    session.end_soc = snap.usable_battery_level or snap.battery_level
    if snap.charge_limit_soc:
        session.charge_limit_soc = snap.charge_limit_soc
    if power and (session.max_power_kw is None or power > session.max_power_kw):
        session.max_power_kw = power


def _gap_exceeded(session: _Session, snap: VehicleSnapshot, threshold_minutes: int) -> bool:
    if not session.snapshots:
        return False
    last = session.snapshots[-1].observed_at
    return (snap.observed_at - last) >= timedelta(minutes=threshold_minutes)


async def _emit(
    session: _Session,
    nominal_kwh: float | None,
    db: AsyncSession,
) -> ChargeSession | None:
    if session.ended_at is None:
        return None

    valid, reason = session.is_valid(nominal_kwh)
    kwh = session.kwh_added(nominal_kwh)
    wall_kwh = round(kwh / DEFAULT_CHARGE_EFFICIENCY, 3) if kwh else None

    avg_power: float | None = None
    voltages = [s.charger_voltage for s in session.snapshots if s.charger_voltage]
    avg_voltage = int(sum(voltages) / len(voltages)) if voltages else None
    phases_vals = [s.charger_phases for s in session.snapshots if s.charger_phases]
    phases = phases_vals[0] if phases_vals else None
    powers = [s.charger_power_kw for s in session.snapshots if s.charger_power_kw]
    if powers:
        avg_power = round(sum(powers) / len(powers), 2)

    # Deduplication: upsert by (vehicle_id, started_at)
    existing = await db.execute(
        select(ChargeSession).where(
            ChargeSession.vehicle_id == session.vehicle_id,
            ChargeSession.started_at == session.started_at,
        )
    )
    record = existing.scalar_one_or_none()

    if record is None:
        record = ChargeSession(
            id=uuid.uuid4(),
            vehicle_id=session.vehicle_id,
            started_at=session.started_at,
        )
        db.add(record)

    record.ended_at = session.ended_at
    record.start_soc = session.start_soc
    record.end_soc = session.end_soc
    record.charge_limit_soc = session.charge_limit_soc
    record.battery_kwh_added = kwh
    record.wall_kwh_estimated = wall_kwh
    record.charge_efficiency = DEFAULT_CHARGE_EFFICIENCY if kwh else None
    record.avg_power_kw = avg_power
    record.max_power_kw = session.max_power_kw
    record.avg_voltage = avg_voltage
    record.phases = phases
    record.has_gap = session.has_gap
    record.incomplete = session.ended_at is None
    record.invalid = not valid
    record.invalid_reason = reason

    await db.flush()
    log.info(
        "Session %s: %s→%s SoC, %.2f kWh, valid=%s",
        record.id, record.start_soc, record.end_soc, kwh or 0, valid,
    )
    return record
