"""
App Settings API — list, upsert, and clear database-backed runtime settings.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.db import get_db
from app.models.app_setting import AppSetting
from app.services.settings_store import SETTING_DEFS, save_setting

router = APIRouter()

_MASKED = "••••••"


class AppSettingOut(BaseModel):
    key: str
    value: str        # masked for secrets: "••••••" if set, "" if not
    is_secret: bool
    is_set: bool      # True when this key exists in the DB (overrides env default)
    label: str
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class AppSettingIn(BaseModel):
    value: str


def _to_out(key: str, row: AppSetting | None) -> AppSettingOut:
    defn = SETTING_DEFS[key]
    if row is None:
        return AppSettingOut(
            key=key,
            value="",
            is_secret=defn["is_secret"],
            is_set=False,
            label=defn["label"],
            updated_at=None,
        )
    masked_value = _MASKED if (row.is_secret and row.value) else (row.value if not row.is_secret else "")
    return AppSettingOut(
        key=key,
        value=masked_value,
        is_secret=row.is_secret,
        is_set=True,
        label=defn["label"],
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[AppSettingOut])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[AppSettingOut]:
    result = await db.execute(select(AppSetting))
    rows_by_key: dict[str, AppSetting] = {r.key: r for r in result.scalars().all()}
    return [_to_out(key, rows_by_key.get(key)) for key in SETTING_DEFS]


@router.put("/{key}", response_model=AppSettingOut)
async def set_setting(
    key: str,
    body: AppSettingIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> AppSettingOut:
    if key not in SETTING_DEFS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown setting: {key!r}")
    row = await save_setting(key, body.value, db)
    return _to_out(key, row)


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> None:
    if key not in SETTING_DEFS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown setting: {key!r}")
    await db.execute(delete(AppSetting).where(AppSetting.key == key))
    await db.commit()
