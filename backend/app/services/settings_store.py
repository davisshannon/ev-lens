"""
Database-backed settings store.

All runtime configuration that used to live only in .env can be overridden
at run-time by writing to the `app_settings` table.  On startup the lifespan
handler calls `load_settings_from_db` which layers DB values on top of the
pydantic-settings defaults.  Secrets are stored encrypted via Fernet.
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.app_setting import AppSetting
from app.security.encryption import decrypt, encrypt

log = logging.getLogger(__name__)

# ── Setting definitions ────────────────────────────────────────────────────────
# is_secret=True  → value is Fernet-encrypted at rest; masked in API responses
SETTING_DEFS: dict[str, dict[str, Any]] = {
    "tesla_client_id":       {"is_secret": False, "label": "Tesla Client ID"},
    "tesla_client_secret":   {"is_secret": True,  "label": "Tesla Client Secret"},
    "app_public_url":        {"is_secret": False, "label": "App Public URL"},
    "oauth_bridge_url":      {"is_secret": False, "label": "OAuth Bridge URL"},
    "anthropic_api_key":     {"is_secret": True,  "label": "Anthropic API Key"},
    "openai_api_key":        {"is_secret": True,  "label": "OpenAI API Key"},
    "xai_api_key":           {"is_secret": True,  "label": "xAI API Key"},
    "aws_access_key_id":     {"is_secret": False, "label": "AWS Access Key ID"},
    "aws_secret_access_key": {"is_secret": True,  "label": "AWS Secret Access Key"},
    "aws_region":            {"is_secret": False, "label": "AWS Region"},
    "ai_model_override":     {"is_secret": False, "label": "AI Model Override"},
}


async def load_settings_from_db(db: AsyncSession) -> None:
    """Load all AppSetting rows and apply them to the global settings object."""
    result = await db.execute(select(AppSetting))
    rows = result.scalars().all()
    for row in rows:
        try:
            value = decrypt(row.value) if row.is_secret else row.value
            setattr(settings, row.key, value)
        except Exception:
            log.warning("Failed to load setting %r from DB — skipping", row.key)
    log.info("Loaded %d setting(s) from database", len(rows))


async def save_setting(key: str, value: str, db: AsyncSession) -> AppSetting:
    """
    Validate, encrypt (if secret), upsert, and apply a setting.

    Returns the persisted AppSetting row.
    """
    if key not in SETTING_DEFS:
        raise ValueError(f"Unknown setting key: {key!r}")

    defn = SETTING_DEFS[key]
    is_secret: bool = defn["is_secret"]
    stored_value = encrypt(value) if is_secret else value

    # PostgreSQL upsert
    stmt = (
        pg_insert(AppSetting)
        .values(key=key, value=stored_value, is_secret=is_secret)
        .on_conflict_do_update(
            index_elements=["key"],
            set_={"value": stored_value, "updated_at": func.now()},
        )
        .returning(AppSetting)
    )
    result = await db.execute(stmt)
    await db.commit()
    row = result.scalar_one()

    # Keep the in-memory settings object in sync
    setattr(settings, key, value)

    return row
