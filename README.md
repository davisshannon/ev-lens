# EV Lens

A local-first EV intelligence platform. Know what your EV is doing, what it costs, how the battery is aging, when to charge, and whether anything looks wrong — without surrendering your data.

## Quick Start

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, SECRET_KEY, ENCRYPTION_KEY at minimum
docker compose up
```

Frontend: http://localhost:3000  
Backend API docs: http://localhost:8000/api/docs

## Requirements

- Docker + Docker Compose
- Tesla Developer account (for Fleet API — see [docs/tesla-setup.md](docs/tesla-setup.md))

## Architecture

```
frontend/   React + Vite + TypeScript + Tailwind (PWA)
backend/    Python FastAPI + SQLAlchemy + Alembic
            PostgreSQL 16
```

See [docs/architecture.md](docs/architecture.md) for full design.

## Development

```bash
# Backend
cd backend
pip install -e ".[dev]"
DATABASE_URL=postgresql+asyncpg://... alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## License

MIT
