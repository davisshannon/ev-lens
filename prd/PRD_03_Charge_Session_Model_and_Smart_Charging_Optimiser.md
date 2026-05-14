# PRD 3: Charge Session Model and Smart Charging Optimiser

## 3.1 Objective

Build the first killer workflow:

"What is the smartest, cheapest, safest way to charge my car tonight, and did it actually work?"

## 3.2 User Stories

1. As an EV owner, I want to set a target SoC and departure time so the system can calculate when charging should start.
2. As a TOU-tariff user, I want the system to minimise charging cost.
3. As a solar owner, I want to know whether to charge from solar, grid, or both.
4. As a cautious owner, I want to reduce time spent sitting at high SoC when not needed.
5. As a user with a 32A wall connector, I want to know whether 16A is enough overnight or whether 32A is required.
6. As a user, I want a post-charge report comparing the plan against actual results.

## 3.3 Functional Requirements

### Charge Session Detection

Detect charge sessions from telemetry:

- plug connected;
- charging started;
- charging stopped;
- SoC start/end;
- kWh added;
- estimated wall energy if available;
- charge current;
- voltage;
- phases if available;
- location;
- charger type;
- cost estimate;
- efficiency estimate.

### Tariff Engine

Support:

- flat rate;
- time-of-use windows;
- EV-specific night window;
- feed-in tariff;
- seasonal tariffs;
- weekday/weekend distinction;
- manual override for one-off price periods.

Example tariff object:

```json
{
  "name": "Home EV Night Plan",
  "currency": "AUD",
  "timezone": "Australia/Melbourne",
  "import_rates": [
    {
      "label": "off_peak",
      "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
      "start": "00:00",
      "end": "06:00",
      "price_per_kwh": 0.08
    },
    {
      "label": "general",
      "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
      "start": "06:00",
      "end": "00:00",
      "price_per_kwh": 0.30
    }
  ],
  "export_rate_per_kwh": 0.05
}
```

### Charging Plan

Inputs:

- current SoC;
- target SoC;
- target departure time;
- estimated usable battery capacity;
- max charger current;
- voltage;
- phase count;
- expected charging efficiency;
- tariff;
- solar forecast, optional;
- home load limits, optional;
- user preference:
  - cheapest;
  - fastest;
  - battery-friendly;
  - solar-maximising;
  - phase/load-safe.

Outputs:

- recommended start time;
- recommended stop time;
- recommended current;
- expected kWh to battery;
- expected wall kWh;
- expected cost;
- expected SoC at departure;
- confidence;
- explanation.

### Post-charge Report

After the session, generate:

- planned vs actual start;
- planned vs actual stop;
- planned vs actual kWh;
- planned vs actual cost;
- planned vs actual SoC;
- charging efficiency;
- derating events;
- interruptions;
- recommendation for next time.

## 3.4 Optimisation Rules

MVP optimiser can be deterministic. Do not use AI for the core charge schedule.

Formula:

```text
required_battery_kwh = usable_capacity_kwh * ((target_soc - current_soc) / 100)
required_wall_kwh = required_battery_kwh / expected_efficiency
charge_power_kw = voltage * amps * phases / 1000
required_hours = required_wall_kwh / charge_power_kw
```

Then choose the cheapest time windows before departure that provide enough total charge time.

## 3.5 Data Model

### tariffs

```sql
CREATE TABLE tariffs (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  currency TEXT DEFAULT 'AUD',
  timezone TEXT NOT NULL,
  config JSONB NOT NULL,
  is_default BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### charge_sessions

```sql
CREATE TABLE charge_sessions (
  id UUID PRIMARY KEY,
  vehicle_id UUID REFERENCES vehicles(id),
  location_id UUID,
  started_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ,
  start_soc_pct DOUBLE PRECISION,
  end_soc_pct DOUBLE PRECISION,
  battery_kwh_added DOUBLE PRECISION,
  wall_kwh_estimated DOUBLE PRECISION,
  efficiency_pct DOUBLE PRECISION,
  avg_power_kw DOUBLE PRECISION,
  max_power_kw DOUBLE PRECISION,
  avg_amps DOUBLE PRECISION,
  max_amps DOUBLE PRECISION,
  voltage DOUBLE PRECISION,
  phases INTEGER,
  cost_estimated NUMERIC,
  currency TEXT DEFAULT 'AUD',
  raw JSONB
);
```

### charge_plans

```sql
CREATE TABLE charge_plans (
  id UUID PRIMARY KEY,
  vehicle_id UUID REFERENCES vehicles(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  current_soc_pct DOUBLE PRECISION NOT NULL,
  target_soc_pct DOUBLE PRECISION NOT NULL,
  departure_time TIMESTAMPTZ NOT NULL,
  recommended_start_time TIMESTAMPTZ NOT NULL,
  recommended_stop_time TIMESTAMPTZ NOT NULL,
  recommended_amps DOUBLE PRECISION,
  expected_battery_kwh DOUBLE PRECISION,
  expected_wall_kwh DOUBLE PRECISION,
  expected_cost NUMERIC,
  confidence TEXT,
  explanation TEXT,
  inputs JSONB NOT NULL,
  result JSONB NOT NULL
);
```

## 3.6 API Endpoints

```http
GET /api/tariffs
POST /api/tariffs
PUT /api/tariffs/{tariff_id}
POST /api/vehicles/{vehicle_id}/charge-plan
GET /api/vehicles/{vehicle_id}/charge-plans/latest
GET /api/vehicles/{vehicle_id}/charge-sessions
GET /api/vehicles/{vehicle_id}/charge-sessions/{session_id}
GET /api/vehicles/{vehicle_id}/charge-sessions/{session_id}/report
```

## 3.7 Acceptance Criteria

- User can create a tariff.
- User can create a charge plan from current SoC to target SoC.
- System returns start time, stop time, current, expected kWh, expected cost, and explanation.
- System handles insufficient time before departure.
- System recommends lower current if lower current is sufficient and user selects battery/load-safe mode.
- Completed charge session generates post-charge report.
- Optimiser unit tests cover flat rate, TOU, insufficient window, and multi-window cases.

## 3.8 Claude/Codex Build Prompt

```text
Build the smart charging module for EV Lens.

Implement charge session detection, tariff configuration, charge planning, and post-charge reporting. Use deterministic optimisation, not LLMs. Add database tables for tariffs, charge_sessions, and charge_plans. Implement API endpoints to create tariffs, generate charge plans, list charge sessions, and produce session reports. Include unit tests for required kWh calculation, TOU window selection, insufficient time handling, lower-current recommendation, and planned-vs-actual comparison.
```

---
