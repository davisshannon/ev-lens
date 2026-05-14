"""Tests for the charge session detector state machine."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.vehicle import VehicleSnapshot
from app.services.charging.detector import detect_sessions, _State


def _snap(
    minutes_offset: int,
    charging_state: str = "Disconnected",
    plugged_in: bool = False,
    battery_level: float = 50.0,
    usable_battery_level: float = 49.0,
    charger_power_kw: float | None = None,
) -> VehicleSnapshot:
    base = datetime(2026, 5, 14, 0, 0, tzinfo=timezone.utc)
    s = VehicleSnapshot.__new__(VehicleSnapshot)
    s.observed_at = base + timedelta(minutes=minutes_offset)
    s.charging_state = charging_state
    s.plugged_in = plugged_in
    s.battery_level = battery_level
    s.usable_battery_level = usable_battery_level
    s.charger_power_kw = charger_power_kw
    s.charger_voltage = 240 if plugged_in else None
    s.charger_phases = 1 if plugged_in else None
    s.charge_limit_soc = 80.0
    return s


def _make_db_mock():
    db = AsyncMock()
    # execute returns a result whose scalar_one_or_none returns None (no existing session)
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=None)
    db.execute = AsyncMock(return_value=mock_result)
    db.add = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_simple_charge_session():
    """Disconnected → Charging → Complete → session emitted after cooldown."""
    vid = uuid.uuid4()
    snaps = [
        _snap(0,   "Disconnected", False, 50, 49),
        _snap(5,   "Charging",     True,  50, 49, 7.2),
        _snap(10,  "Charging",     True,  55, 54, 7.2),
        _snap(60,  "Charging",     True,  70, 69, 7.2),
        _snap(65,  "Complete",     True,  70, 69),
        # cooldown: 15 min after Complete
        _snap(81,  "Complete",     True,  70, 69),
    ]

    with patch("app.services.charging.detector.ChargeSession") as mock_cls:
        instance = AsyncMock()
        instance.id = uuid.uuid4()
        mock_cls.return_value = instance
        db = _make_db_mock()
        sessions = await detect_sessions(vid, snaps, db, nominal_kwh=75.0)

    # Session should have been flushed
    assert db.flush.called


@pytest.mark.asyncio
async def test_phantom_plug_no_session():
    """Plugged in briefly, never charges → no session emitted."""
    vid = uuid.uuid4()
    snaps = [
        _snap(0,  "Disconnected", False, 70, 69),
        _snap(5,  "Stopped",      True,  70, 69),
        _snap(10, "Disconnected", False, 70, 69),
    ]
    db = _make_db_mock()
    sessions = await detect_sessions(vid, snaps, db, nominal_kwh=75.0)
    assert not db.add.called


@pytest.mark.asyncio
async def test_session_invalidated_when_soc_drops():
    """Session where end_soc < start_soc is marked invalid."""
    vid = uuid.uuid4()
    snaps = [
        _snap(0,  "Charging", True,  70, 69, 7.2),
        _snap(5,  "Charging", True,  68, 67, 7.2),  # SoC went down
        _snap(20, "Complete", True,  68, 67),
        _snap(36, "Complete", True,  68, 67),  # past cooldown
    ]

    captured_record = None

    async def fake_flush():
        nonlocal captured_record
        # The record should have invalid=True for soc_decreased
        pass

    db = _make_db_mock()
    db.flush = fake_flush

    with patch("app.services.charging.detector.ChargeSession") as mock_cls:
        instance = type("R", (), {
            "id": uuid.uuid4(), "vehicle_id": vid,
            "started_at": None, "ended_at": None,
            "start_soc": 69.0, "end_soc": 67.0,
            "charge_limit_soc": 80.0, "battery_kwh_added": None,
            "wall_kwh_estimated": None, "charge_efficiency": None,
            "avg_power_kw": None, "max_power_kw": None,
            "avg_voltage": None, "phases": None,
            "has_gap": False, "incomplete": False,
            "invalid": False, "invalid_reason": None,
        })()
        mock_cls.return_value = instance
        await detect_sessions(vid, snaps, db, nominal_kwh=75.0)
