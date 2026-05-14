"""Import API — TeslaMate PostgreSQL import endpoints."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth
from app.db import get_db
from app.models.imports import ImportBatch
from app.schemas.imports import ImportBatchOut, TeslamateImportRequest
from app.services.imports.teslamate import rollback_batch, run_teslamate_import

log = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# POST /teslamate/dry-run
# ---------------------------------------------------------------------------

@router.post("/teslamate/dry-run", response_model=ImportBatchOut)
async def teslamate_dry_run(
    body: TeslamateImportRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> ImportBatch:
    batch = ImportBatch(
        id=uuid.uuid4(),
        source_type="teslamate",
        status="dry_run",
        dry_run=True,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    try:
        summary = await run_teslamate_import(
            db_url=body.db_url,
            ev_db=db,
            batch=batch,
            vehicle_id=body.vehicle_id,
            dry_run=True,
        )
        batch.status = "completed"
        batch.summary = summary
        batch.completed_at = datetime.now(timezone.utc)
    except Exception as exc:
        log.exception("Dry-run failed: %s", exc)
        batch.status = "failed"
        batch.error = str(exc)
        batch.completed_at = datetime.now(timezone.utc)

    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return batch


# ---------------------------------------------------------------------------
# POST /teslamate/import
# ---------------------------------------------------------------------------

@router.post("/teslamate/import", response_model=ImportBatchOut, status_code=status.HTTP_202_ACCEPTED)
async def teslamate_import(
    body: TeslamateImportRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> ImportBatch:
    batch = ImportBatch(
        id=uuid.uuid4(),
        source_type="teslamate",
        status="running",
        dry_run=False,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    # Fire-and-forget background task
    asyncio.create_task(
        _run_import_background(
            batch_id=batch.id,
            db_url=body.db_url,
            vehicle_id=body.vehicle_id,
        )
    )

    return batch


async def _run_import_background(
    batch_id: uuid.UUID,
    db_url: str,
    vehicle_id: uuid.UUID | None,
) -> None:
    """Run the actual import in a background task with its own DB session."""
    from app.db import AsyncSessionLocal  # avoid circular at module level

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ImportBatch).where(ImportBatch.id == batch_id)
        )
        batch = result.scalar_one_or_none()
        if batch is None:
            log.error("Background import: batch %s not found", batch_id)
            return

        try:
            summary = await run_teslamate_import(
                db_url=db_url,
                ev_db=db,
                batch=batch,
                vehicle_id=vehicle_id,
                dry_run=False,
            )
            batch.status = "completed"
            batch.summary = summary
            batch.completed_at = datetime.now(timezone.utc)
        except Exception as exc:
            log.exception("Background import failed (batch=%s): %s", batch_id, exc)
            batch.status = "failed"
            batch.error = str(exc)
            batch.completed_at = datetime.now(timezone.utc)

        db.add(batch)
        await db.commit()


# ---------------------------------------------------------------------------
# GET /{batch_id}
# ---------------------------------------------------------------------------

@router.get("/{batch_id}", response_model=ImportBatchOut)
async def get_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> ImportBatch:
    result = await db.execute(
        select(ImportBatch).where(ImportBatch.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return batch


# ---------------------------------------------------------------------------
# GET / (list recent batches)
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[ImportBatchOut])
async def list_batches(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> list[ImportBatch]:
    result = await db.execute(
        select(ImportBatch)
        .order_by(ImportBatch.started_at.desc())
        .limit(min(limit, 100))
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# POST /{batch_id}/rollback
# ---------------------------------------------------------------------------

@router.post("/{batch_id}/rollback", response_model=ImportBatchOut)
async def rollback_import(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> ImportBatch:
    result = await db.execute(
        select(ImportBatch).where(ImportBatch.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    if batch.status not in ("completed",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot rollback a batch with status '{batch.status}'",
        )

    try:
        await rollback_batch(db, batch)
    except Exception as exc:
        log.exception("Rollback failed (batch=%s): %s", batch_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {exc}",
        ) from exc

    await db.refresh(batch)
    return batch
