"""
Integrations API — configure Wall Connector, Powerwall, and future integrations.
Sensitive values (passwords, tokens) are encrypted before storage.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.db import get_db
from app.models.integration import Integration
from app.security.encryption import encrypt
from app.services.integrations.powerwall import PowerwallClient
from app.services.integrations.wall_connector import WallConnectorClient

router = APIRouter()


class IntegrationOut(BaseModel):
    id: uuid.UUID
    integration_type: str
    name: str
    enabled: bool
    last_success_at: datetime | None
    last_error: str | None

    model_config = {"from_attributes": True}


class WallConnectorIn(BaseModel):
    host: str
    name: str = "Wall Connector"


class PowerwallIn(BaseModel):
    host: str
    password: str
    email: str = "customer@example.com"
    name: str = "Powerwall"


@router.get("", response_model=list[IntegrationOut])
async def list_integrations(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[Integration]:
    result = await db.execute(select(Integration).order_by(Integration.created_at))
    return list(result.scalars().all())


@router.post("/wall-connector", response_model=IntegrationOut, status_code=status.HTTP_201_CREATED)
async def add_wall_connector(
    body: WallConnectorIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> Integration:
    # Test connectivity before saving
    client = WallConnectorClient(host=body.host)
    vitals = await client.get_vitals()
    if vitals is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not reach Wall Connector at {body.host}. Check the IP and ensure EV Lens is on the same network.",
        )

    integration = Integration(
        id=uuid.uuid4(),
        integration_type="wall_connector",
        name=body.name,
        enabled=True,
        config={"host": body.host},
        last_success_at=datetime.now(timezone.utc),
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration


@router.post("/powerwall", response_model=IntegrationOut, status_code=status.HTTP_201_CREATED)
async def add_powerwall(
    body: PowerwallIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> Integration:
    # Test connectivity + auth before saving
    client = PowerwallClient(host=body.host, password=body.password, email=body.email)
    agg = await client.get_aggregates()
    if agg is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not reach Powerwall at {body.host}. Check the IP and password (last 5 digits of serial number).",
        )

    integration = Integration(
        id=uuid.uuid4(),
        integration_type="powerwall",
        name=body.name,
        enabled=True,
        config={
            "host": body.host,
            "password_encrypted": encrypt(body.password),
            "email": body.email,
        },
        last_success_at=datetime.now(timezone.utc),
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration


@router.patch("/{integration_id}/toggle", response_model=IntegrationOut)
async def toggle_integration(
    integration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> Integration:
    result = await db.execute(select(Integration).where(Integration.id == integration_id))
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
    integration.enabled = not integration.enabled
    await db.commit()
    await db.refresh(integration)
    return integration


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> None:
    result = await db.execute(select(Integration).where(Integration.id == integration_id))
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
    await db.delete(integration)
    await db.commit()
