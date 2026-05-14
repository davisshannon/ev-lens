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
