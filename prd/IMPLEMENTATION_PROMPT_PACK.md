# EV Lens Implementation Prompt Pack

Use these prompts sequentially with Claude Code or Codex.

## Prompt 1: Create Skeleton

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

## Prompt 2: Charge Planning Engine

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

## Prompt 3: TeslaMate Import

Build TeslaMate import support.

Create import_batches and import_mappings tables.
Implement dry-run import from a read-only TeslaMate PostgreSQL connection.
Map vehicles, drives, charge sessions, and geofences into EV Lens schema.
Show summary counts, skipped rows, duplicate detection, and rollback support.
Never write to the TeslaMate source database.

## Prompt 4: Alerts

Build deterministic alert detectors for:
- vampire drain
- charging efficiency drop
- charging derating
- interrupted charging
- provider data gaps

Alerts must include severity, confidence, evidence, possible causes, and recommended actions.
Avoid duplicate alert spam.
Add tests for normal, anomalous, and insufficient-baseline cases.

## Prompt 5: AI Explanations

Build an AI explanation endpoint that answers telemetry questions only from provided structured context.

Questions to support:
- Why did my Tesla lose battery overnight?
- Why did charging take longer than expected?
- Why did charging speed drop?
- Is my battery health estimate reliable?
- Was that drive inefficient?

The LLM response must include:
- Answer
- Evidence
- Confidence
- What to do next

The LLM must not invent data or issue vehicle commands.
Add output validation and tests.
