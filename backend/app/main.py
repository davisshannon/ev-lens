import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, vehicles, tariffs, charges, battery, alerts, ai, imports, integrations, auth
from app.config import settings

logging.basicConfig(level=settings.log_level.upper())
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from app.workers.poller import start_poller
    from app.workers.energy_poller import start_energy_poller
    from app.services.first_run import maybe_create_admin
    await maybe_create_admin()
    tasks = [
        asyncio.create_task(start_poller()),
        asyncio.create_task(start_energy_poller()),
    ]
    log.info("Background workers started")
    yield
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(
    lifespan=lifespan,
    title="EV Lens",
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened via env in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(vehicles.router, prefix="/api/v1/vehicles", tags=["vehicles"])
app.include_router(tariffs.router, prefix="/api/v1/tariffs", tags=["tariffs"])
app.include_router(charges.router, prefix="/api/v1/charges", tags=["charges"])
app.include_router(battery.router, prefix="/api/v1/battery", tags=["battery"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(imports.router, prefix="/api/v1/imports", tags=["imports"])
app.include_router(integrations.router, prefix="/api/v1/integrations", tags=["integrations"])
