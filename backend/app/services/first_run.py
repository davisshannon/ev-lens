"""Creates the admin user on first boot if FIRST_RUN_ADMIN_PASSWORD is set."""

import logging

from sqlalchemy import select

from app.config import settings
from app.db import AsyncSessionLocal
from app.models.user import User
from app.security.auth import hash_password

log = logging.getLogger(__name__)


async def maybe_create_admin() -> None:
    if not settings.first_run_admin_password:
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none():
            return

        admin = User(
            username="admin",
            hashed_password=hash_password(settings.first_run_admin_password),
            is_active=True,
            is_admin=True,
        )
        db.add(admin)
        await db.commit()
        log.info("Admin user created. Remove FIRST_RUN_ADMIN_PASSWORD from env.")
