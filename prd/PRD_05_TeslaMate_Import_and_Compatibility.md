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
