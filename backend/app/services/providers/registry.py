"""
Provider registry: resolves a live VehicleProvider for a given vehicle
by loading + decrypting its credentials from the integrations table.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import Integration
from app.security.encryption import decrypt
from app.services.providers.base import VehicleProvider
from app.services.providers.tesla import TeslaProvider


async def get_provider_for_vehicle(vehicle_id: str, db: AsyncSession) -> VehicleProvider | None:
    result = await db.execute(
        select(Integration).where(
            Integration.integration_type == "tesla_fleet",
            Integration.enabled.is_(True),
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        return None

    encrypted_token = integration.config.get("access_token_encrypted")
    if not encrypted_token:
        return None

    access_token = decrypt(encrypted_token)
    return TeslaProvider(access_token=access_token)
