from datetime import datetime, timezone

import pytest

from app.services.charging.tariff import rate_at, cheapest_window, cost_for_kwh

TOU_CONFIG = {
    "type": "tou",
    "windows": [
        {"name": "off_peak", "start": "00:00", "end": "06:00", "days": list(range(7)), "rate": 0.08},
        {"name": "peak",     "start": "16:00", "end": "21:00", "days": list(range(5)),  "rate": 0.38},
        {"name": "shoulder", "start": "06:00", "end": "16:00", "days": list(range(7)), "rate": 0.25},
    ],
    "default_rate": 0.25,
    "currency": "USD",
}

EV_NIGHT_CONFIG = {
    "type": "ev_night",
    "night_start": "00:30",
    "night_end": "07:30",
    "night_rate": 0.07,
    "day_rate": 0.28,
}

FLAT_CONFIG = {"type": "flat", "rate": 0.22}


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 5, 14, hour, minute, tzinfo=timezone.utc)


def test_flat_rate():
    r = rate_at(FLAT_CONFIG, _utc(14), "UTC")
    assert r.rate == pytest.approx(0.22)
    assert r.window_name == "flat"


def test_tou_off_peak():
    r = rate_at(TOU_CONFIG, _utc(3), "UTC")
    assert r.rate == pytest.approx(0.08)
    assert r.window_name == "off_peak"


def test_tou_peak():
    r = rate_at(TOU_CONFIG, _utc(18), "UTC")
    assert r.rate == pytest.approx(0.38)
    assert r.window_name == "peak"


def test_tou_shoulder():
    r = rate_at(TOU_CONFIG, _utc(10), "UTC")
    assert r.rate == pytest.approx(0.25)
    assert r.window_name == "shoulder"


def test_ev_night_in_window():
    r = rate_at(EV_NIGHT_CONFIG, _utc(3), "UTC")
    assert r.rate == pytest.approx(0.07)
    assert r.window_name == "night"


def test_ev_night_outside_window():
    r = rate_at(EV_NIGHT_CONFIG, _utc(12), "UTC")
    assert r.rate == pytest.approx(0.28)
    assert r.window_name == "day"


def test_cheapest_window_tou():
    window = cheapest_window(TOU_CONFIG, "UTC", _utc(9))
    assert window is not None
    assert window.name == "off_peak"
    assert window.rate == pytest.approx(0.08)


def test_cost_for_kwh():
    cost = cost_for_kwh(TOU_CONFIG, 10.0, _utc(3), "UTC")  # off-peak rate
    assert cost == pytest.approx(0.80)
