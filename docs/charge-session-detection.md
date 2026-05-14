# Charge Session Detection

This document defines how EV Lens detects charge sessions from vehicle snapshots. It must be read before implementing any code in `services/charging/`.

---

## Overview

EV Lens does not receive a "charging started" event from Tesla. Instead, it infers charge sessions by running a detector over the time-series of `vehicle_snapshots`. The detector maintains a state machine per vehicle and emits `charge_sessions` records when a session is considered complete.

---

## State Machine

Each vehicle tracks one of four states:

```
IDLE ──────────────────────────────────────────────────────► IDLE
  │                                                             ▲
  │ plugged_in = true                                           │
  ▼                                                             │
PLUGGED_IN ──── charging_state = "Charging" ──────────────► CHARGING
  │                                                             │
  │ plugged_in = false                                          │ plugged_in = false
  │ (never started charging)                                    │ OR charging_state = "Complete"
  ▼                                                             │
IDLE (no session emitted)                                       ▼
                                                            COMPLETING
                                                                │
                                                                │ after cooldown window (15 min)
                                                                │ with no resumption
                                                                ▼
                                                            session emitted → IDLE
```

### States

| State | Meaning |
|-------|---------|
| `IDLE` | Vehicle is not plugged in |
| `PLUGGED_IN` | Vehicle is plugged in but `charging_state` is `Stopped`, `NoPower`, or `Starting` |
| `CHARGING` | `charging_state = "Charging"` — active energy transfer |
| `COMPLETING` | `charging_state = "Complete"` or unplugged — waiting for cooldown before emitting |

---

## Transition Rules

### IDLE → PLUGGED_IN
Trigger: snapshot where `plugged_in = true` AND `charging_state` is not `"Charging"`.

### IDLE → CHARGING (fast path)
Trigger: snapshot where `plugged_in = true` AND `charging_state = "Charging"`.  
Reason: some snapshots are sparse and we may miss the PLUGGED_IN moment.

### PLUGGED_IN → CHARGING
Trigger: snapshot where `charging_state = "Charging"`.

### PLUGGED_IN → IDLE
Trigger: snapshot where `plugged_in = false`.  
Action: discard — no session emitted (plugged in but never charged).

### CHARGING → COMPLETING
Trigger: any of:
- `charging_state = "Complete"`
- `charging_state = "Stopped"` AND SoC >= target SoC (or target SoC not set)
- `plugged_in = false`

### COMPLETING → IDLE (session emitted)
Trigger: cooldown window of **15 minutes** elapses with no snapshot returning to `charging_state = "Charging"`.  
Action: emit a `charge_session` record, reset to IDLE.

### COMPLETING → CHARGING (resumption)
Trigger: snapshot within the cooldown window where `charging_state = "Charging"`.  
Reason: handles brief interruptions (power fluctuation, TOU switch, scheduled limit change).  
Action: return to CHARGING, extend session.

---

## Session Boundaries

### Session start
`started_at` = timestamp of first snapshot where `charging_state = "Charging"` for this session.

### Session end
`ended_at` = timestamp of last snapshot where `charging_state = "Charging"` (before cooldown expired).

### SoC delta
`start_soc` = `usable_battery_level` at `started_at`.  
`end_soc` = `usable_battery_level` at `ended_at`.

### Energy added
`battery_kwh_added` is computed from SoC delta × estimated usable capacity.  
`wall_kwh_estimated` = `battery_kwh_added / charge_efficiency` (default 0.88 if no Wall Connector data).  
If Wall Connector telemetry is available, use actual power integral instead.

---

## Gap and Missing Snapshot Handling

### Short gap (< 15 minutes)
If snapshots stop arriving mid-session (polling failure, vehicle asleep), treat as a pause — remain in `CHARGING` state. When snapshots resume:
- If still `charging_state = "Charging"`: continue the session.
- If `charging_state = "Complete"` or unplugged: enter COMPLETING with `ended_at` set to last known charging snapshot.

### Long gap (15–60 minutes)
If no snapshot for 15–60 minutes while in `CHARGING`:
- Enter a `CHARGING_GAP` sub-state.
- When snapshots resume and charging has ended: emit session with a `has_gap = true` flag and note the gap interval in `raw_jsonb`.
- When snapshots resume and still charging: continue normally.

### Very long gap (> 60 minutes)
If no snapshot for > 60 minutes while in `CHARGING`:
- Emit a partial session with `incomplete = true` up to the last known snapshot.
- When snapshots resume: if charging again, start a new session (cannot safely merge).

### Overnight / multi-day sessions
No special handling needed — the state machine handles these naturally as long as snapshots continue arriving. The 15-minute cooldown window is short enough that a legitimate multi-hour overnight charge will never accidentally close.

---

## Midnight Boundary

Sessions that cross midnight are **not split**. `started_at` and `ended_at` are stored as UTC; UI is responsible for displaying in the vehicle's local timezone.

---

## Multiple Vehicles

The state machine runs independently per `vehicle_id`. No cross-vehicle state sharing.

---

## Session Invalidation

A session is marked `invalid = true` and excluded from analysis if:
- `end_soc < start_soc` (SoC went down — likely a range mode or data anomaly)
- Duration < 2 minutes (phantom plug event)
- `battery_kwh_added < 0.1 kWh` (below measurement noise floor)

Invalid sessions are retained in the database for debugging but excluded from all aggregations.

---

## Concurrency / Re-processing

The detector is **idempotent**: running it over the same snapshot window twice must not produce duplicate sessions. Sessions are identified by `(vehicle_id, started_at)` with a unique constraint. On re-run, existing sessions in the window are diffed and updated if their `ended_at` or SoC values change (e.g., due to a late-arriving snapshot).

---

## Relationship to Wall Connector Data

If Wall Connector telemetry is available for the same time window, it is used to:
1. Confirm `plugged_in` state (ground-truth for session boundaries).
2. Replace the SoC-derived `wall_kwh_estimated` with a direct power integral.
3. Populate `avg_power_kw`, `max_power_kw`, `voltage`, `phases` on the session.

Wall Connector data enriches sessions but is never required. If absent, estimation proceeds from SoC delta alone.

---

## Powerwall Interaction

During a session, if Powerwall data is available:
- Tag session with `energy_source`: `grid`, `solar`, `powerwall`, or `mixed`.
- Record `grid_kwh`, `solar_kwh`, `powerwall_kwh` breakdown on the session.
- Use this for cost calculation (solar = $0, grid = tariff rate).

---

## Tesla `charging_state` Values

Reference values from the Fleet API for the state machine:

| Value | Meaning |
|-------|---------|
| `Charging` | Active energy transfer |
| `Complete` | Charge complete, still plugged in |
| `Stopped` | Plugged in, charging halted (scheduled, limit reached, user stopped) |
| `NoPower` | Plugged in, no power available |
| `Starting` | Initialising charge session |
| `Disconnected` | Not plugged in |

---

## Configuration

These values are configurable per-installation (with defaults):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `charge_cooldown_minutes` | 15 | Time after charging stops before session is emitted |
| `charge_gap_threshold_minutes` | 15 | Gap duration before entering CHARGING_GAP sub-state |
| `charge_split_threshold_minutes` | 60 | Gap duration before splitting into separate sessions |
| `min_session_duration_seconds` | 120 | Sessions shorter than this are invalidated |
| `min_session_kwh` | 0.1 | Sessions below this energy are invalidated |
| `default_charge_efficiency` | 0.88 | AC-to-battery efficiency if no Wall Connector data |
