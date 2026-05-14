# EV Intelligence Platform PRDs

Version: 0.1  
Target users: technically capable EV owners, TeslaMate users, Home Assistant users, solar/TOU-tariff households, later small fleets  
Primary build agents: Claude Code and Codex  
Working product name: **EV Lens**  
Primary wedge: **local-first EV telemetry + smart charging intelligence + modern UX**

---

## 0. Current Landscape and Source Assumptions

These PRDs assume the following current platform realities:

1. TeslaMate is a strong self-hosted logger using Elixir, PostgreSQL, Grafana, and MQTT. Its strengths are data collection, dashboards, geofencing, charging/drive logs, MQTT integration, and self-hosted ownership. Its weaknesses are product UX, setup friction, mobile experience, and guided explanation.
2. Tesla Fleet Telemetry is Tesla's preferred efficient path for real-time vehicle data because vehicles can stream directly to a server instead of forcing repeated polling of vehicle_data. This matters because polling can wake vehicles and increase battery drain.
3. Tesla Fleet API has moved into a priced access model from 2025, so API efficiency, event-driven telemetry, caching, and careful polling strategy are product requirements, not optimisations.
4. TeslaMate currently defaults to unofficial Owner API/streaming flows for individuals, with official Fleet API/Fleet Telemetry paths needed in some account/API contexts. This creates an API-abstraction requirement.
5. The product should avoid being Tesla-only at the domain-model level. Tesla should be the first provider, not the permanent architecture boundary.

References checked:
- TeslaMate GitHub and documentation
- Tesla Fleet API and Fleet Telemetry documentation
- Tesla Fleet API announcements
- TeslaMate API configuration documentation
- Home Assistant Tesla Fleet integration documentation
- Tesla Wall Connector local/API ecosystem references

---

# PRD 1: Platform Vision and Product Scope

## 1.1 Problem

EV owners who care about cost, battery health, charging behaviour, and home energy context have to choose between:

- self-hosted telemetry tools with strong data ownership but weak UX;
- polished cloud apps with weaker privacy/control;
- smart home integrations that are powerful but fragmented;
- manual spreadsheet-style reasoning for tariff, solar, charging current, and departure-time decisions.

The market gap is not another Tesla dashboard. The gap is a **modern EV intelligence layer** that turns telemetry into decisions and explanations.

## 1.2 Product Thesis

Build a local-first EV telemetry and charging intelligence platform that gives owners:

- self-hosted control similar to TeslaMate;
- polished consumer UX similar to Tessie/TeslaFi-style apps;
- smart charging recommendations based on tariffs, solar, home load, and departure time;
- explainable battery health estimates with confidence scoring;
- anomaly detection for vampire drain, charge derating, poor efficiency, and unusual behaviour;
- optional AI-assisted explanations grounded strictly in telemetry;
- extensibility through MQTT, Home Assistant, REST, webhooks, and future provider plugins.

## 1.3 Non-goals

Do not build these in the first phase:

- social leaderboards;
- insurance scoring;
- public fleet comparison;
- trip-planner clone;
- aggressive remote vehicle-control feature set;
- FSD/safety scoring claims;
- Tesla-only naming/branding;
- mobile-native apps before the PWA proves value;
- full commercial fleet management in MVP.

## 1.4 Target Users

### Primary Persona: Technical EV Owner

- Owns a Tesla or comparable connected EV.
- May already use TeslaMate, Home Assistant, solar monitoring, or smart energy tools.
- Wants local data ownership.
- Wants better answers than Grafana charts.
- Is willing to run Docker but expects a guided setup.

### Secondary Persona: Solar/TOU Optimiser

- Has solar, time-of-use electricity pricing, or EV night tariffs.
- Wants the cheapest and smartest charge plan.
- Does not care about raw telemetry unless it improves decisions.

### Later Persona: Small Fleet / Family Fleet

- Multiple vehicles.
- Wants cost allocation, charge reports, and anomaly alerts.
- Needs a hosted or managed deployment option.

## 1.5 Core User Promise

"Know what your EV is doing, what it costs, how the battery is aging, when to charge, and whether anything looks wrong, without surrendering your data by default."

## 1.6 Success Criteria

The MVP is successful if a user can:

1. Connect one Tesla.
2. Collect telemetry and charge sessions reliably for at least 14 days.
3. View current vehicle state, drives, charge sessions, and cost history in a modern UI.
4. Configure their tariff and home charger.
5. Receive a recommended charge plan for a target SoC and departure time.
6. Compare the completed charge against the plan.
7. Get at least basic battery health estimation with a confidence rating.
8. Export data and/or migrate from TeslaMate.
9. Use the system without exposing ports directly to the public internet.

---

# PRD 2: Local Collector and Vehicle Provider Layer

## 2.1 Objective

Build a local collector service that ingests vehicle data through a provider abstraction. Tesla is the first provider, but the internal domain model must support future providers.

## 2.2 Core Requirements

### Functional Requirements

1. Support a provider interface:

```typescript
interface VehicleProvider {
  providerName: string;
  authenticate(): Promise<AuthResult>;
  listVehicles(): Promise<VehicleSummary[]>;
  getVehicleSnapshot(vehicleId: string): Promise<VehicleSnapshot>;
  subscribeTelemetry?(vehicleId: string): AsyncIterable<TelemetryEvent>;
  getChargeState(vehicleId: string): Promise<ChargeState>;
  getDriveState(vehicleId: string): Promise<DriveState>;
  getVehicleConfig(vehicleId: string): Promise<VehicleConfig>;
}
```

2. Implement `TeslaProvider`.
3. Support both snapshot polling and future streaming/telemetry ingestion.
4. Avoid unnecessary vehicle wakeups.
5. Persist raw provider payloads where useful for debugging, but normalise data into canonical tables.
6. Track provider API health, rate-limit errors, authentication errors, and data gaps.
7. Store tokens encrypted at rest.
8. Support local-only operation.
9. Provide clear setup status:
   - provider connected;
   - token valid;
   - vehicle discovered;
   - latest telemetry received;
   - polling/streaming mode active;
   - last error.

### Non-functional Requirements

- Collector must be restart-safe.
- No data loss during short service interruptions.
- Polling frequency must be configurable.
- Default polling must be conservative and sleep-safe.
- Logs must not expose tokens.
- The service must run on Docker Compose.
- Support ARM64 and AMD64 images.

## 2.3 Suggested Stack

Preferred:

- Backend: Python FastAPI or TypeScript Node/NestJS.
- Worker: Python asyncio / Celery / Dramatiq or Node worker queues.
- Database: PostgreSQL with TimescaleDB extension preferred.
- Cache/queue: Redis optional, not required in MVP.
- Frontend: Next.js or Vite React.
- Auth: local admin account for MVP.
- Deployment: Docker Compose.

Reasonable MVP choice:

- Python FastAPI backend
- PostgreSQL/TimescaleDB
- React + Vite frontend
- Docker Compose

## 2.4 Data Model

### vehicles

```sql
CREATE TABLE vehicles (
  id UUID PRIMARY KEY,
  provider TEXT NOT NULL,
  provider_vehicle_id TEXT NOT NULL,
  vin TEXT,
  display_name TEXT,
  model TEXT,
  trim TEXT,
  year INTEGER,
  timezone TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(provider, provider_vehicle_id)
);
```

### vehicle_snapshots

```sql
CREATE TABLE vehicle_snapshots (
  id BIGSERIAL PRIMARY KEY,
  vehicle_id UUID REFERENCES vehicles(id),
  observed_at TIMESTAMPTZ NOT NULL,
  provider TEXT NOT NULL,
  state TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  odometer_km DOUBLE PRECISION,
  battery_level_pct DOUBLE PRECISION,
  usable_battery_level_pct DOUBLE PRECISION,
  estimated_range_km DOUBLE PRECISION,
  rated_range_km DOUBLE PRECISION,
  ideal_range_km DOUBLE PRECISION,
  outside_temp_c DOUBLE PRECISION,
  inside_temp_c DOUBLE PRECISION,
  is_climate_on BOOLEAN,
  is_sentry_mode BOOLEAN,
  raw JSONB
);
```

### provider_events

```sql
CREATE TABLE provider_events (
  id BIGSERIAL PRIMARY KEY,
  provider TEXT NOT NULL,
  vehicle_id UUID REFERENCES vehicles(id),
  event_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  message TEXT NOT NULL,
  raw JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## 2.5 API Endpoints

```http
GET /api/health
GET /api/providers
POST /api/providers/tesla/connect
GET /api/vehicles
GET /api/vehicles/{vehicle_id}
GET /api/vehicles/{vehicle_id}/snapshot/latest
GET /api/vehicles/{vehicle_id}/provider-health
POST /api/collector/poll-now
```

## 2.6 Acceptance Criteria

- A user can deploy with Docker Compose and open the web UI.
- A user can connect Tesla provider credentials.
- At least one vehicle appears in the UI.
- Latest vehicle snapshot is shown.
- Snapshots persist across container restarts.
- Provider errors are visible in the UI.
- Tokens are never printed in logs.
- No public internet exposure is required.

## 2.7 Claude/Codex Build Prompt

```text
Build the local collector and provider abstraction for EV Lens.

Use Python FastAPI, PostgreSQL, SQLAlchemy/Alembic, and Docker Compose. Create a provider interface and implement a TeslaProvider stub that can later be wired to real Tesla auth/API calls. Build the schema for vehicles, vehicle_snapshots, and provider_events. Create REST endpoints for health, provider status, vehicles, latest snapshot, and manual poll. Add structured logging with token redaction. Include tests for database persistence, provider error handling, and API responses. Do not implement unsafe remote vehicle commands in this phase.
```

---

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

# PRD 4: Modern Web/PWA User Interface

## 4.1 Objective

Replace Grafana-first UX with a modern web app that answers ownership questions directly.

## 4.2 Navigation

Primary navigation:

```text
Today
Charging
Battery
Drives
Costs
Alerts
Settings
```

Later:

```text
Home Energy
Garage
Automations
Ask
```

## 4.3 Screens

### Today

Purpose: daily summary.

Cards:

- current SoC;
- location;
- plugged-in status;
- target/departure;
- recommended charge start;
- latest drive efficiency;
- last 24h drain;
- active alerts.

Example copy:

```text
Current SoC: 63%
Target: 80% by 7:00am
Recommended start: 12:35am at 32A
Expected cost: $2.84
Confidence: High
```

### Charging

Features:

- current charging status;
- charge plan form;
- tariff selector;
- amperage selector;
- recent charge sessions;
- planned vs actual chart;
- efficiency trend.

### Battery

Features:

- estimated usable capacity;
- degradation trend;
- confidence score;
- calibration quality;
- charge habits;
- high-SoC dwell time;
- battery-friendly recommendations.

### Drives

Features:

- drive list;
- efficiency;
- distance;
- energy;
- elevation if available;
- map optional;
- compare against baseline.

### Costs

Features:

- monthly charge cost;
- home vs away;
- tariff breakdown;
- solar vs grid if integrated;
- cost per 100 km;
- export CSV.

### Alerts

Features:

- unusual drain;
- charger derating;
- interrupted charge;
- unusually poor efficiency;
- provider/API issues;
- battery-estimate confidence degradation.

### Settings

Features:

- vehicle provider;
- tariff;
- home charger;
- home location;
- privacy/export;
- backup;
- integrations;
- telemetry polling mode.

## 4.4 Design Requirements

- Mobile-first.
- Responsive desktop layout.
- Light/dark mode.
- No Grafana dependency for primary user workflows.
- Grafana can remain optional/export-only later.
- Use plain explanations, not raw telemetry field names.
- Every recommendation must show "why".

## 4.5 Suggested Frontend Stack

- React + Vite or Next.js
- TypeScript
- Tailwind
- Recharts
- TanStack Query
- Zustand or Redux Toolkit only if needed
- PWA support

## 4.6 API Contracts

Frontend should consume REST APIs from backend.

Example charge-plan response:

```json
{
  "vehicle_id": "uuid",
  "current_soc_pct": 63,
  "target_soc_pct": 80,
  "departure_time": "2026-05-15T07:00:00+10:00",
  "recommended_start_time": "2026-05-15T00:35:00+10:00",
  "recommended_stop_time": "2026-05-15T03:12:00+10:00",
  "recommended_amps": 32,
  "expected_wall_kwh": 19.8,
  "expected_cost": 1.58,
  "confidence": "high",
  "explanation": [
    "Off-peak pricing is available from 00:00 to 06:00.",
    "32A charging provides enough energy in approximately 2h 37m.",
    "Starting at 00:35 completes well before departure while avoiding unnecessary time at high SoC."
  ]
}
```

## 4.7 Acceptance Criteria

- User can complete onboarding from empty state.
- User can see current vehicle summary.
- User can generate a charge plan on mobile.
- User can view recent charge sessions.
- User can understand why a recommendation was made.
- UI handles provider disconnected/error state gracefully.
- PWA install works on mobile browser.
- No page requires Grafana.

## 4.8 Claude/Codex Build Prompt

```text
Build the EV Lens frontend as a modern TypeScript React PWA.

Implement Today, Charging, Battery, Drives, Costs, Alerts, and Settings screens. Use Tailwind, TanStack Query, and Recharts. Consume the backend REST APIs. Focus on mobile-first layouts and clear explanations. Include empty states, loading states, error states, and mocked API fixtures for local frontend development. Do not depend on Grafana for any primary user workflow.
```

---

# PRD 5: TeslaMate Import and Compatibility

## 5.1 Objective

Allow existing TeslaMate users to migrate or mirror their data so EV Lens can start with historical context.

## 5.2 Use Cases

1. User exports TeslaMate PostgreSQL data and imports it into EV Lens.
2. User connects EV Lens read-only to a TeslaMate database.
3. User imports charge sessions, drive sessions, geofences, vehicle metadata, and odometer/battery snapshots.
4. User validates imported data before committing.

## 5.3 Functional Requirements

### Import Modes

MVP:

- file-based import from CSV/SQL export where feasible;
- direct Postgres read-only import later.

Preferred v0.2:

- direct TeslaMate Postgres connection;
- schema detection;
- dry-run preview;
- import mapping report;
- incremental import.

### Data to Import

- vehicles;
- positions/snapshots;
- drives;
- charging processes/sessions;
- addresses/geofences;
- update/version events where available;
- charge costs if available.

### Import Safety

- never write to TeslaMate DB;
- support dry run;
- report counts;
- report skipped rows;
- detect duplicate vehicles/sessions;
- allow rollback of an import batch.

## 5.4 Data Model

### import_batches

```sql
CREATE TABLE import_batches (
  id UUID PRIMARY KEY,
  source_type TEXT NOT NULL,
  source_version TEXT,
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL,
  summary JSONB,
  error TEXT
);
```

### import_mappings

```sql
CREATE TABLE import_mappings (
  id UUID PRIMARY KEY,
  import_batch_id UUID REFERENCES import_batches(id),
  source_table TEXT NOT NULL,
  source_id TEXT NOT NULL,
  target_table TEXT NOT NULL,
  target_id TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## 5.5 API Endpoints

```http
POST /api/imports/teslamate/dry-run
POST /api/imports/teslamate/run
GET /api/imports
GET /api/imports/{import_batch_id}
POST /api/imports/{import_batch_id}/rollback
```

## 5.6 Acceptance Criteria

- User can run a dry-run import.
- System reports expected vehicles, drives, charge sessions, and skipped records.
- User can run import after preview.
- Imported charge sessions appear in Charging screen.
- Imported drives appear in Drives screen.
- Import does not require TeslaMate downtime.
- Import cannot mutate TeslaMate source database.

## 5.7 Claude/Codex Build Prompt

```text
Build TeslaMate import support for EV Lens.

Create import_batches and import_mappings tables. Implement a dry-run import framework that can map TeslaMate vehicles, drives, charging sessions, and geofences into the EV Lens schema. Start with a direct PostgreSQL read-only connection mode and make the mapping layer isolated so CSV import can be added later. Include duplicate detection, summary reporting, skipped-row reporting, and rollback by import batch. Never write to the source TeslaMate database.
```

---

# PRD 6: Battery Health and Confidence Model

## 6.1 Objective

Provide battery health insight without pretending noisy estimates are exact.

## 6.2 Problem

Most EV battery estimates are too confident. Vehicle-reported range, SoC, temperature, calibration state, charging window, and BMS behaviour can distort estimates.

The product should make uncertainty visible.

## 6.3 Core Features

- estimated usable battery capacity;
- degradation from nominal/new estimate;
- trend over time;
- calibration quality;
- confidence score;
- explanation of evidence quality;
- charge-habit insights.

## 6.4 Confidence Inputs

Confidence should consider:

- number of charge sessions;
- size of charge sessions in kWh;
- SoC range covered;
- sessions ending above 80%;
- sessions starting below 20–30%;
- temperature range;
- consistency of estimated capacity;
- recentness of data;
- odometer coverage;
- data gaps.

## 6.5 Confidence Levels

```text
Unknown: insufficient data
Low: noisy or sparse data
Moderate: enough data for directional estimate
High: repeated high-quality sessions with consistent estimates
```

## 6.6 Output Example

```json
{
  "estimated_usable_capacity_kwh": 76.4,
  "nominal_capacity_kwh": 79.0,
  "estimated_degradation_pct": 3.3,
  "confidence": "moderate",
  "evidence": {
    "charge_sessions_used": 18,
    "large_sessions_used": 6,
    "soc_span_quality": "medium",
    "temperature_adjusted": false,
    "recentness": "good"
  },
  "explanation": [
    "Estimate is based on 18 sessions, but only 6 added more than 20 kWh.",
    "Few low-to-high SoC sessions are available, so confidence is moderate rather than high.",
    "The latest estimate is consistent with the prior 30-day trend."
  ]
}
```

## 6.7 Data Model

### battery_estimates

```sql
CREATE TABLE battery_estimates (
  id UUID PRIMARY KEY,
  vehicle_id UUID REFERENCES vehicles(id),
  calculated_at TIMESTAMPTZ DEFAULT now(),
  estimated_usable_capacity_kwh DOUBLE PRECISION,
  nominal_capacity_kwh DOUBLE PRECISION,
  estimated_degradation_pct DOUBLE PRECISION,
  confidence TEXT NOT NULL,
  evidence JSONB NOT NULL,
  explanation JSONB NOT NULL
);
```

## 6.8 Acceptance Criteria

- System produces "unknown" until enough data exists.
- System produces a confidence-scored capacity estimate after enough charge sessions.
- UI explains why confidence is low/moderate/high.
- System does not present degradation as overly precise.
- Battery estimate is recalculated after new qualifying charge sessions.
- Tests cover insufficient data, noisy data, and stable data.

## 6.9 Claude/Codex Build Prompt

```text
Build the EV Lens battery health module.

Implement a battery capacity estimation service using charge session data. Add confidence scoring based on data quantity, session size, SoC span, consistency, and recentness. Store estimates in battery_estimates. Expose API endpoints for latest estimate and historical estimates. The UI/API must never present battery degradation without a confidence level and evidence summary. Include tests for insufficient, noisy, moderate, and high-confidence data cases.
```

---

# PRD 7: Anomaly Detection and Explainable Alerts

## 7.1 Objective

Detect unusual EV behaviour and explain it using telemetry evidence.

## 7.2 Anomaly Types

MVP:

- unusual overnight/vampire drain;
- unexpected wakeups;
- charging efficiency drop;
- charging current derating;
- interrupted charging;
- unusually poor drive efficiency;
- provider/API data gaps.

Later:

- post-software-update behavioural shifts;
- tyre/pressure efficiency drift;
- HVAC-heavy consumption;
- location-specific charging issues;
- home electrical/load warning patterns.

## 7.3 Detection Philosophy

Use deterministic/statistical baselines first. AI may explain results, but it must not be the source of truth for detection.

Pattern:

```text
baseline → current observation → deviation → confidence → evidence → recommendation
```

## 7.4 Alert Object

```json
{
  "type": "charging_efficiency_drop",
  "severity": "medium",
  "confidence": "moderate",
  "title": "Charging efficiency was unusually low",
  "summary": "Last night's charging efficiency was 78%, compared with your normal home baseline of 91-94%.",
  "evidence": [
    "Session started at 00:12 and ended at 04:44.",
    "Estimated wall energy was 31.2 kWh.",
    "Battery energy added was 24.4 kWh.",
    "No comparable low-efficiency session was seen in the prior 30 days."
  ],
  "possible_causes": [
    "battery conditioning",
    "voltage sag",
    "charger derating",
    "measurement mismatch",
    "cold weather"
  ],
  "recommended_actions": [
    "Check whether HVAC or battery preconditioning was active.",
    "Review wall connector current and voltage during the session.",
    "Watch the next two home sessions before changing hardware assumptions."
  ]
}
```

## 7.5 Data Model

### alerts

```sql
CREATE TABLE alerts (
  id UUID PRIMARY KEY,
  vehicle_id UUID REFERENCES vehicles(id),
  alert_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  confidence TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  evidence JSONB NOT NULL,
  possible_causes JSONB,
  recommended_actions JSONB,
  status TEXT DEFAULT 'open',
  created_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ
);
```

## 7.6 Detection Rules

### Vampire Drain

Inputs:

- parked duration;
- SoC start/end;
- sentry mode;
- cabin overheat protection;
- climate state;
- wake/sleep events;
- software update events if available.

Alert if:

- drain exceeds user baseline by threshold;
- or drain exceeds fixed absolute threshold where no baseline exists.

### Charging Efficiency Drop

Inputs:

- wall kWh;
- battery kWh;
- session location;
- temperature;
- charger current/voltage;
- prior home sessions.

Alert if:

- efficiency falls below baseline by configurable threshold.

### Derating

Inputs:

- expected charger power;
- observed power;
- current limit;
- voltage;
- interruptions.

Alert if:

- observed power persistently below configured expected power without user-selected amperage reduction.

## 7.7 Acceptance Criteria

- Alerts are generated deterministically from telemetry.
- Alerts include evidence and confidence.
- User can dismiss/resolve alerts.
- Same alert is not spammed repeatedly.
- Alerts link back to relevant session/snapshot.
- Tests cover normal, anomalous, and insufficient-baseline cases.

## 7.8 Claude/Codex Build Prompt

```text
Build the EV Lens anomaly detection and alerting module.

Implement deterministic detectors for vampire drain, charging efficiency drop, charging derating, interrupted charging, poor drive efficiency, and provider data gaps. Store alerts with severity, confidence, evidence, possible causes, and recommended actions. Add APIs to list, resolve, and inspect alerts. Make detectors baseline-aware and avoid spamming duplicate alerts. Include tests for normal behaviour, anomalous behaviour, and insufficient-baseline behaviour.
```

---

# PRD 8: AI Explanation Layer

## 8.1 Objective

Add natural-language explanations grounded in telemetry and alerts.

This is not a generic chatbot. It is an evidence renderer and reasoning assistant over structured data.

## 8.2 Core Principle

The model may explain, summarise, and compare. It must not invent telemetry or issue vehicle commands.

## 8.3 MVP Questions

Support these question types:

```text
Why did my Tesla lose battery overnight?
Why did charging take longer than expected?
Why did charging speed drop?
Was last night's charge cheaper than usual?
Is my battery health estimate reliable?
Was that drive inefficient?
What should I change before tonight's charge?
```

## 8.4 Retrieval Context

For each question, backend should collect relevant structured context before calling an LLM:

- latest vehicle state;
- relevant charge sessions;
- relevant drive sessions;
- alerts;
- tariff;
- weather, optional;
- home energy, optional;
- battery estimate;
- confidence values.

## 8.5 Response Format

```markdown
### Answer
Brief answer.

### Evidence
- Specific telemetry point
- Specific session
- Specific comparison against baseline

### Confidence
High / Moderate / Low

### What to do next
- Action 1
- Action 2
```

## 8.6 Guardrails

- No remote vehicle commands.
- No unsupported safety claims.
- No medical/legal/insurance claims.
- Do not infer location-sensitive details unless already visible to the user.
- If data is insufficient, say so.
- Every answer must cite internal telemetry objects by ID or timestamp.
- LLM output should be validated to ensure it includes evidence and confidence.

## 8.7 Data Model

### ai_explanations

```sql
CREATE TABLE ai_explanations (
  id UUID PRIMARY KEY,
  vehicle_id UUID REFERENCES vehicles(id),
  user_question TEXT NOT NULL,
  context_summary JSONB NOT NULL,
  answer_markdown TEXT NOT NULL,
  confidence TEXT NOT NULL,
  model TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## 8.8 Acceptance Criteria

- User can ask supported telemetry questions.
- Backend retrieves relevant context deterministically.
- Response includes answer, evidence, confidence, and next steps.
- If insufficient data exists, response says so.
- LLM is not allowed to issue commands.
- Tests validate output structure.

## 8.9 Claude/Codex Build Prompt

```text
Build the EV Lens AI explanation layer.

Create a backend service that answers natural-language questions about vehicle telemetry using deterministic retrieval over charge sessions, drive sessions, alerts, battery estimates, and tariff data. The LLM should only explain provided context. It must not invent data or issue vehicle commands. Responses must include Answer, Evidence, Confidence, and What to do next. Store explanations in ai_explanations. Include schema validation for model output and tests for insufficient-data, charging-delay, vampire-drain, and battery-confidence questions.
```

---

# PRD 9: Home Energy and Integrations

## 9.1 Objective

Connect EV charging behaviour to home energy context.

## 9.2 Integrations

MVP:

- manual tariff configuration;
- Home Assistant webhook/API import;
- MQTT output.

v0.2:

- Tesla Wall Connector local telemetry where available;
- Fronius inverter data;
- solar production;
- home load;
- Powerwall, if applicable;
- OCPP chargers.

## 9.3 Requirements

### Home Assistant

- Pull or receive entities:
  - solar generation;
  - grid import/export;
  - home load;
  - charger power;
  - charger current;
  - vehicle presence;
  - tariff sensor if available.
- Allow mapping HA entity IDs to EV Lens fields.

### MQTT

Publish:

```text
evlens/{vehicle_id}/state
evlens/{vehicle_id}/charging
evlens/{vehicle_id}/battery
evlens/{vehicle_id}/alerts
evlens/{vehicle_id}/charge_plan
```

Subscribe later:

```text
evlens/{vehicle_id}/target_soc
evlens/{vehicle_id}/departure_time
```

### Wall Connector

If supported:

- read connected status;
- session energy;
- current;
- voltage;
- phase data;
- charger temperature/status if available.

## 9.4 Data Model

### home_energy_samples

```sql
CREATE TABLE home_energy_samples (
  id BIGSERIAL PRIMARY KEY,
  observed_at TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,
  solar_kw DOUBLE PRECISION,
  grid_import_kw DOUBLE PRECISION,
  grid_export_kw DOUBLE PRECISION,
  home_load_kw DOUBLE PRECISION,
  charger_kw DOUBLE PRECISION,
  raw JSONB
);
```

### integrations

```sql
CREATE TABLE integrations (
  id UUID PRIMARY KEY,
  integration_type TEXT NOT NULL,
  name TEXT NOT NULL,
  config JSONB NOT NULL,
  enabled BOOLEAN DEFAULT true,
  last_success_at TIMESTAMPTZ,
  last_error TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## 9.5 Acceptance Criteria

- User can configure Home Assistant integration.
- User can map HA entities to energy fields.
- System stores home energy samples.
- Charge reports can include wall/home energy where available.
- MQTT publishes current state and alerts.
- Integration failures are visible.

## 9.6 Claude/Codex Build Prompt

```text
Build the EV Lens home energy integration module.

Implement integration records, Home Assistant entity mapping, home_energy_samples storage, and MQTT publishing for vehicle state, charging, battery, alerts, and charge plans. Add APIs and UI settings for configuring Home Assistant URL/token and entity mappings. Include tests for sample ingestion, invalid mappings, MQTT payload generation, and integration error reporting.
```

---

# PRD 10: Security, Privacy, and Deployment

## 10.1 Objective

Make the product safe enough for local vehicle telemetry and token handling.

## 10.2 Security Requirements

- Encrypt provider tokens at rest.
- Never log access/refresh tokens.
- Use local admin authentication.
- Require password change from default.
- Support disabling all cloud features.
- No default public exposure.
- Explicit warnings if bound to public interface.
- CORS locked down by default.
- Secrets via environment variables or local secret store.
- Backup/restore support.
- Audit log for provider connection, import, settings changes, and AI questions.

## 10.3 Deployment Modes

### MVP

Docker Compose:

```text
backend
frontend
postgres/timescaledb
optional mqtt
```

### Later

- Home Assistant add-on;
- Synology package;
- Proxmox/LXC guide;
- hosted SaaS;
- hybrid sync relay.

## 10.4 Backup Requirements

- one-click backup export;
- scheduled database backup;
- restore documented;
- backup includes DB data but not plaintext secrets;
- encryption key warning shown clearly.

## 10.5 Acceptance Criteria

- Fresh install requires local admin setup.
- Tokens encrypted at rest.
- Logs redacted.
- Backups can be generated and restored.
- Security warning if user tries to expose service publicly.
- Docker Compose install works on Linux AMD64 and ARM64.

## 10.6 Claude/Codex Build Prompt

```text
Build EV Lens security and deployment foundations.

Implement local admin authentication, encrypted token storage, log redaction, audit logging, Docker Compose deployment, backup/export, and restore documentation. Ensure no public exposure is required. Add startup checks for missing encryption key, default password, and unsafe bind settings. Include tests for token encryption, log redaction, auth enforcement, and backup command generation.
```

---

# PRD 11: MVP Milestones

## Milestone 0: Repo and Skeleton

Deliverables:

- monorepo;
- backend service;
- frontend app;
- Docker Compose;
- Postgres/TimescaleDB;
- migrations;
- test framework;
- CI.

Acceptance:

- `docker compose up` starts the stack.
- frontend loads;
- backend health endpoint works;
- database migration runs.

## Milestone 1: Vehicle Collector

Deliverables:

- provider abstraction;
- Tesla provider stub/real connector depending on API availability;
- vehicle list;
- latest snapshot;
- provider health.

Acceptance:

- one vehicle appears;
- snapshots persist;
- errors visible.

## Milestone 2: Charge Sessions and Tariffs

Deliverables:

- charge session model;
- tariff engine;
- charge plan API;
- post-charge report.

Acceptance:

- user can generate plan from current SoC to target SoC;
- charge session report compares plan vs actual.

## Milestone 3: Modern UI

Deliverables:

- Today screen;
- Charging screen;
- Settings/onboarding;
- basic Battery and Costs screens.

Acceptance:

- mobile-first UI supports primary workflow without Grafana.

## Milestone 4: TeslaMate Import

Deliverables:

- dry run;
- import;
- rollback;
- mapping report.

Acceptance:

- imported charge sessions and drives visible.

## Milestone 5: Battery Confidence and Alerts

Deliverables:

- battery estimate;
- confidence scoring;
- alerts for drain, derating, interruption, efficiency drop.

Acceptance:

- alerts include evidence and confidence;
- battery health never shown without confidence.

## Milestone 6: AI Explanation Layer

Deliverables:

- supported question templates;
- deterministic context retrieval;
- LLM response validation;
- explanation history.

Acceptance:

- answers include evidence, confidence, and next steps.

---

# PRD 12: Repository Structure

Recommended monorepo:

```text
ev-lens/
  README.md
  docker-compose.yml
  .env.example

  backend/
    app/
      main.py
      config.py
      db.py
      models/
      schemas/
      api/
      services/
        providers/
          base.py
          tesla.py
        charging/
        battery/
        alerts/
        ai/
        imports/
        integrations/
      security/
      workers/
    alembic/
    tests/
    pyproject.toml

  frontend/
    src/
      app/
      components/
      pages/
      api/
      hooks/
      stores/
      charts/
      types/
    package.json
    vite.config.ts

  docs/
    architecture.md
    api.md
    deployment.md
    security.md
    teslamate-import.md
    charging-optimizer.md

  scripts/
    backup.sh
    restore.sh
    dev-seed.py
```

---

# PRD 13: Initial Backlog

## P0

- Docker Compose boots.
- Backend health endpoint.
- Database migrations.
- Local admin auth.
- Vehicle provider abstraction.
- Tesla provider connection placeholder.
- Vehicle/snapshot schema.
- Tariff schema.
- Charge-plan calculation.
- Today and Charging UI.
- Settings UI.
- Token encryption.
- Log redaction.

## P1

- Charge session detection.
- Post-charge report.
- TeslaMate dry-run import.
- Battery confidence estimate.
- Basic alerts.
- Home Assistant integration.
- MQTT publishing.

## P2

- AI explanation layer.
- Fronius integration.
- Wall Connector integration.
- Software update impact analysis.
- Hosted sync architecture.
- Native mobile app.

---

# PRD 14: First Claude Code Task

```text
You are building EV Lens, a local-first EV telemetry and smart charging platform.

Create the initial monorepo with:
- backend: Python FastAPI, SQLAlchemy, Alembic, PostgreSQL
- frontend: Vite React TypeScript, Tailwind, TanStack Query
- deployment: Docker Compose
- database: PostgreSQL, compatible with TimescaleDB later
- auth: local admin login skeleton
- modules: providers, charging, battery, alerts, imports, integrations

Implement:
1. backend health endpoint
2. database connection and migrations
3. vehicles table
4. vehicle_snapshots table
5. tariffs table
6. charge_plans table
7. provider abstraction
8. Tesla provider stub
9. charge planning service with deterministic calculation
10. frontend Today and Charging pages using mocked + real API fallback
11. .env.example
12. README with local setup

Do not implement real Tesla auth yet unless the required credentials and API path are provided.
Do not implement remote vehicle commands.
Include tests for the charge planning calculation and backend health endpoint.
```

---

# PRD 15: First Codex Task

```text
Implement the deterministic charge planning engine.

Inputs:
- current_soc_pct
- target_soc_pct
- usable_capacity_kwh
- departure_time
- now
- voltage
- amps
- phases
- expected_efficiency_pct
- tariff windows
- user mode: cheapest | fastest | battery_friendly | load_safe

Outputs:
- required_battery_kwh
- required_wall_kwh
- recommended_start_time
- recommended_stop_time
- recommended_amps
- expected_cost
- confidence
- explanation[]

Rules:
- Validate target_soc > current_soc.
- Validate departure_time > now.
- Calculate required kWh.
- Calculate charging power.
- Prefer cheapest tariff windows before departure.
- If battery_friendly or load_safe mode can succeed at lower amps, recommend lower amps.
- If insufficient time exists, return a structured insufficient_time result.
- Always include explanation strings.
- Add unit tests for flat tariff, TOU tariff, insufficient time, lower-amp success, and multi-window scheduling.
```

---

# PRD 16: Open Questions

These should be resolved before implementation beyond MVP skeleton:

1. Will the first implementation use official Tesla Fleet API from day one, or start with stubs/import while credentials/API registration are handled separately?
2. Should the product be self-hosted-only initially, or designed for hosted/hybrid from day one?
3. Is Home Assistant integration mandatory for v0.1 or v0.2?
4. Should Fronius support be direct, via Home Assistant, or both?
5. Should Wall Connector telemetry be treated as best-effort because local access is not a formal stable product API?
6. Is the first user only one vehicle, or should multi-vehicle be part of the initial data model? This PRD assumes multi-vehicle schema but one-vehicle UI.
7. Should AI explanations use local models, hosted APIs, or pluggable provider configuration?
8. What is the product name? Avoid Tesla-specific names.

---

# Final Product Definition

EV Lens is not a TeslaMate clone.

It is a local-first EV intelligence platform that uses vehicle telemetry, charge sessions, tariff data, home energy context, and explainable anomaly detection to answer practical ownership questions.

The first product should win on one question:

**What is the smartest, cheapest, safest way to charge my car tonight, and did it actually work?**
