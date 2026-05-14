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
