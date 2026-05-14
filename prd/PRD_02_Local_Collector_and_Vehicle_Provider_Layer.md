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
