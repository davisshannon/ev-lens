import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.db import get_db
from app.models.integration import Integration
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.vehicle import TeslaAuthUrlOut
from app.security.auth import create_access_token, verify_password
from app.security.encryption import encrypt
from app.services.providers.tesla import TeslaAuthService, TeslaProvider

router = APIRouter()
_auth_service = TeslaAuthService()

# In-memory state store (single-instance only; replace with Redis for multi-instance)
_pending_states: dict[str, float] = {}
STATE_TTL_S = 600  # 10 min to complete OAuth


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TeslaCallbackIn(BaseModel):
    code: str
    state: str


@router.post("/token", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    from app.models.user import User as U
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/tesla/url", response_model=TeslaAuthUrlOut)
async def tesla_auth_url(_: str = Depends(require_auth)) -> TeslaAuthUrlOut:
    """Generate Tesla OAuth URL. User opens this in their browser."""
    auth_url, state = _auth_service.generate_auth_url()
    _pending_states[state] = time.time()
    # Prune expired states
    expired = [s for s, t in _pending_states.items() if time.time() - t > STATE_TTL_S]
    for s in expired:
        del _pending_states[s]
    return TeslaAuthUrlOut(auth_url=auth_url, state=state)


@router.post("/tesla/callback")
async def tesla_callback(
    body: TeslaCallbackIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> dict:
    """
    Receives the OAuth code forwarded by the auth bridge.
    Exchanges for tokens, stores encrypted, discovers vehicles.
    """
    # Verify state to prevent CSRF
    issued_at = _pending_states.pop(body.state, None)
    if issued_at is None or time.time() - issued_at > STATE_TTL_S:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state")

    tokens = await _auth_service.exchange_code(body.code)

    # Store integration record with encrypted tokens
    integration = Integration(
        integration_type="tesla_fleet",
        name="Tesla Fleet API",
        enabled=True,
        config={
            "access_token_encrypted": encrypt(tokens["access_token"]),
            "refresh_token_encrypted": encrypt(tokens["refresh_token"]),
            "expires_at": time.time() + tokens.get("expires_in", 3600),
        },
        last_success_at=datetime.now(timezone.utc),
    )
    db.add(integration)
    await db.flush()

    # Discover and persist vehicles
    provider = TeslaProvider(access_token=tokens["access_token"])
    vehicle_infos = await provider.list_vehicles()
    created = []

    for info in vehicle_infos:
        existing = await db.execute(
            select(Vehicle).where(
                Vehicle.provider == "tesla_fleet",
                Vehicle.provider_vehicle_id == info.provider_vehicle_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        vehicle = Vehicle(
            id=uuid.uuid4(),
            provider="tesla_fleet",
            provider_vehicle_id=info.provider_vehicle_id,
            vin=info.vin,
            display_name=info.display_name,
            model=info.model,
            year=info.year,
        )
        db.add(vehicle)
        created.append(info.display_name or info.provider_vehicle_id)

    await db.commit()
    return {"status": "connected", "vehicles_added": created}
