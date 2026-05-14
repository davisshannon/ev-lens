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
