"""
Tariff engine.

Tariff config schema (stored as JSONB in tariffs.config):

Flat rate:
  {"type": "flat", "rate": 0.25, "export_rate": 0.08}

Time-of-use:
  {
    "type": "tou",
    "windows": [
      {"name": "off_peak", "start": "00:00", "end": "06:00", "days": [0,1,2,3,4,5,6], "rate": 0.08},
      {"name": "peak",     "start": "16:00", "end": "21:00", "days": [0,1,2,3,4],     "rate": 0.38},
      {"name": "shoulder", "start": "06:00", "end": "16:00", "days": [0,1,2,3,4,5,6], "rate": 0.25}
    ],
    "default_rate": 0.25
  }

EV night (single cheap window, rest at default):
  {
    "type": "ev_night",
    "night_start": "00:30",
    "night_end":   "07:30",
    "night_rate":  0.07,
    "day_rate":    0.28
  }

Seasonal (wraps any of the above with date-range overrides):
  {"type": "seasonal", "seasons": [...], "default": {...}}
"""

from __future__ import annotations

import zoneinfo
from dataclasses import dataclass
from datetime import datetime, time


@dataclass
class RateWindow:
    name: str
    rate: float          # $/kWh import
    start: time
    end: time
    days: list[int]      # 0=Mon … 6=Sun (ISO weekday - 1)


@dataclass
class TariffRate:
    rate: float
    window_name: str


def rate_at(config: dict, dt: datetime, tz: str) -> TariffRate:
    """Return the applicable rate for a given UTC datetime under this tariff config."""
    local_dt = dt.astimezone(zoneinfo.ZoneInfo(tz))
    tariff_type = config.get("type", "flat")

    if tariff_type == "flat":
        return TariffRate(rate=float(config.get("rate", 0.0)), window_name="flat")

    if tariff_type in ("tou", "ev_night"):
        windows = _build_windows(config)
        return _match_window(local_dt, windows, float(config.get("default_rate", 0.0)))

    if tariff_type == "seasonal":
        return _seasonal_rate(config, local_dt, tz)

    return TariffRate(rate=0.0, window_name="unknown")


def cheapest_window(config: dict, tz: str, date: datetime) -> RateWindow | None:
    """Return the cheapest window on a given day (used for charge planning)."""
    local_dt = date.astimezone(zoneinfo.ZoneInfo(tz))
    windows = _build_windows(config)
    if not windows:
        return None
    day = local_dt.weekday()
    today_windows = [w for w in windows if day in w.days]
    return min(today_windows, key=lambda w: w.rate) if today_windows else None


def cost_for_kwh(config: dict, kwh: float, dt: datetime, tz: str) -> float:
    """Calculate cost for a given kWh amount at a specific time."""
    r = rate_at(config, dt, tz)
    return round(kwh * r.rate, 4)


def _build_windows(config: dict) -> list[RateWindow]:
    t = config.get("type")
    if t == "tou":
        return [
            RateWindow(
                name=w["name"],
                rate=float(w["rate"]),
                start=_parse_time(w["start"]),
                end=_parse_time(w["end"]),
                days=w.get("days", list(range(7))),
            )
            for w in config.get("windows", [])
        ]
    if t == "ev_night":
        return [
            RateWindow(
                name="night",
                rate=float(config["night_rate"]),
                start=_parse_time(config["night_start"]),
                end=_parse_time(config["night_end"]),
                days=list(range(7)),
            ),
            RateWindow(
                name="day",
                rate=float(config["day_rate"]),
                start=_parse_time(config["night_end"]),
                end=_parse_time(config["night_start"]),
                days=list(range(7)),
            ),
        ]
    return []


def _match_window(local_dt: datetime, windows: list[RateWindow], default_rate: float) -> TariffRate:
    t = local_dt.time()
    day = local_dt.weekday()
    for w in windows:
        if day not in w.days:
            continue
        if _time_in_window(t, w.start, w.end):
            return TariffRate(rate=w.rate, window_name=w.name)
    return TariffRate(rate=default_rate, window_name="default")


def _time_in_window(t: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= t < end
    # Overnight window e.g. 23:00–06:00
    return t >= start or t < end


def _seasonal_rate(config: dict, local_dt: datetime, tz: str) -> TariffRate:
    month = local_dt.month
    for season in config.get("seasons", []):
        months = season.get("months", [])
        if month in months:
            return rate_at(season["tariff"], local_dt, tz)
    default = config.get("default", {})
    return rate_at(default, local_dt, tz) if default else TariffRate(rate=0.0, window_name="default")


def _parse_time(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))
