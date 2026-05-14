"""TeslaMate PostgreSQL import service.

Reads from a TeslaMate database and maps its data to EV Lens models:
  - cars             → Vehicle
  - positions        → VehicleSnapshot
  - charging_processes → ChargeSession

Every inserted record is tracked in ImportMapping for rollback support.
Batch inserts use ON CONFLICT DO NOTHING so re-running the same import is safe.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models.imports import ImportBatch, ImportMapping
from app.models.vehicle import Vehicle, VehicleSnapshot
from app.models.charge import ChargeSession

log = logging.getLogger(__name__)

SNAPSHOT_CHUNK = 500


def _asyncpg_url(db_url: str) -> str:
    """Convert a plain postgresql:// URL to postgresql+asyncpg://."""
    for prefix in ("postgresql://", "postgres://"):
        if db_url.startswith(prefix):
            return "postgresql+asyncpg://" + db_url[len(prefix):]
    if db_url.startswith("postgresql+asyncpg://"):
        return db_url
    raise ValueError(f"Unrecognised TeslaMate DB URL scheme: {db_url!r}")


async def run_teslamate_import(
    *,
    db_url: str,
    ev_db: AsyncSession,
    batch: ImportBatch,
    vehicle_id: uuid.UUID | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute (or preview) a TeslaMate import.

    Parameters
    ----------
    db_url:
        Connection string for the TeslaMate PostgreSQL database.
    ev_db:
        Async SQLAlchemy session for the EV Lens database.
    batch:
        The ImportBatch record to update with progress / results.
    vehicle_id:
        When provided, only import data for the EV Lens vehicle with this id.
        The matching TeslaMate car is resolved via VIN or display name.
    dry_run:
        When True, count records that *would* be imported but write nothing.
    """
    summary: dict[str, Any] = {
        "vehicles_found": 0,
        "snapshots_imported": 0,
        "sessions_imported": 0,
        "skipped": 0,
        "errors": 0,
    }

    src_engine = create_async_engine(
        _asyncpg_url(db_url),
        echo=False,
        pool_pre_ping=True,
        # Minimal pool — import is one-shot
        pool_size=2,
        max_overflow=0,
    )
    SrcSession = async_sessionmaker(src_engine, expire_on_commit=False)

    try:
        async with SrcSession() as src:
            cars = await _fetch_cars(src)
            if not cars:
                summary["errors"] += 1
                return summary

            # If a specific EV Lens vehicle was requested, resolve it
            if vehicle_id is not None:
                ev_vehicle = await _get_ev_vehicle(ev_db, vehicle_id)
                if ev_vehicle is None:
                    raise ValueError(f"Vehicle {vehicle_id} not found in EV Lens")
                # Match by VIN first, then display_name
                matched = [
                    c for c in cars
                    if (ev_vehicle.vin and c["vin"] == ev_vehicle.vin)
                    or c["name"] == ev_vehicle.display_name
                ]
                if not matched:
                    raise ValueError(
                        f"No TeslaMate car matches vehicle {vehicle_id} "
                        f"(vin={ev_vehicle.vin}, name={ev_vehicle.display_name})"
                    )
                cars = matched

            summary["vehicles_found"] = len(cars)

            for car in cars:
                try:
                    await _import_car(
                        src=src,
                        ev_db=ev_db,
                        car=car,
                        batch=batch,
                        summary=summary,
                        dry_run=dry_run,
                        pinned_vehicle_id=vehicle_id,
                    )
                except Exception as exc:
                    log.exception("Error importing TeslaMate car id=%s: %s", car["id"], exc)
                    summary["errors"] += 1
    finally:
        await src_engine.dispose()

    return summary


# ---------------------------------------------------------------------------
# Source-DB queries
# ---------------------------------------------------------------------------

async def _fetch_cars(src: AsyncSession) -> list[dict]:
    rows = await src.execute(
        text(
            "SELECT id, vin, name, efficiency FROM cars ORDER BY id"
        )
    )
    return [dict(r._mapping) for r in rows]


async def _fetch_positions(src: AsyncSession, car_id: int) -> list[dict]:
    rows = await src.execute(
        text(
            """
            SELECT
                date,
                battery_level,
                usable_battery_level,
                rated_range_km,
                speed,
                odometer,
                latitude,
                longitude,
                charging_state,
                charger_power
            FROM positions
            WHERE car_id = :car_id
            ORDER BY date
            """
        ),
        {"car_id": car_id},
    )
    return [dict(r._mapping) for r in rows]


async def _fetch_charging_processes(src: AsyncSession, car_id: int) -> list[dict]:
    rows = await src.execute(
        text(
            """
            SELECT
                id,
                start_date,
                end_date,
                start_battery_level,
                end_battery_level,
                charge_energy_added,
                cost
            FROM charging_processes
            WHERE car_id = :car_id
            ORDER BY start_date
            """
        ),
        {"car_id": car_id},
    )
    return [dict(r._mapping) for r in rows]


# ---------------------------------------------------------------------------
# Per-car import logic
# ---------------------------------------------------------------------------

async def _import_car(
    *,
    src: AsyncSession,
    ev_db: AsyncSession,
    car: dict,
    batch: ImportBatch,
    summary: dict[str, Any],
    dry_run: bool,
    pinned_vehicle_id: uuid.UUID | None,
) -> None:
    car_id: int = car["id"]

    if not dry_run:
        if pinned_vehicle_id is not None:
            vehicle = await _get_ev_vehicle(ev_db, pinned_vehicle_id)
        else:
            vehicle = await _upsert_vehicle(ev_db, car, batch)
    else:
        # In dry-run we still need a placeholder id for counting
        vehicle = None

    # --- Positions → VehicleSnapshot ---
    positions = await _fetch_positions(src, car_id)
    if dry_run:
        summary["snapshots_imported"] += len(positions)
    else:
        assert vehicle is not None
        imported, skipped = await _bulk_insert_snapshots(
            ev_db, vehicle, positions, batch, batch_size=SNAPSHOT_CHUNK
        )
        summary["snapshots_imported"] += imported
        summary["skipped"] += skipped

    # --- charging_processes → ChargeSession ---
    charging_processes = await _fetch_charging_processes(src, car_id)
    if dry_run:
        summary["sessions_imported"] += len(charging_processes)
    else:
        assert vehicle is not None
        imported, skipped = await _bulk_insert_sessions(
            ev_db, vehicle, charging_processes, batch
        )
        summary["sessions_imported"] += imported
        summary["skipped"] += skipped


# ---------------------------------------------------------------------------
# Vehicle upsert
# ---------------------------------------------------------------------------

async def _get_ev_vehicle(db: AsyncSession, vehicle_id: uuid.UUID) -> Vehicle | None:
    result = await db.execute(
        text("SELECT * FROM vehicles WHERE id = :id"),
        {"id": str(vehicle_id)},
    )
    row = result.mappings().one_or_none()
    if row is None:
        return None
    # Reconstruct a minimal Vehicle-like object
    v = Vehicle.__new__(Vehicle)
    v.id = row["id"]
    v.vin = row.get("vin")
    v.display_name = row.get("display_name")
    v.provider = row.get("provider")
    v.provider_vehicle_id = row.get("provider_vehicle_id")
    v.nominal_battery_kwh = row.get("nominal_battery_kwh")
    return v


async def _upsert_vehicle(
    db: AsyncSession, car: dict, batch: ImportBatch
) -> Vehicle:
    """Insert or fetch the EV Lens Vehicle for a TeslaMate car row."""
    provider_vehicle_id = str(car["id"])

    # Check existing
    result = await db.execute(
        text(
            "SELECT id FROM vehicles WHERE provider = 'teslamate' AND provider_vehicle_id = :pvid"
        ),
        {"pvid": provider_vehicle_id},
    )
    row = result.one_or_none()

    if row is not None:
        vehicle_id = row[0]
        # Fetch full object via ORM
        result2 = await db.execute(
            text("SELECT * FROM vehicles WHERE id = :id"), {"id": str(vehicle_id)}
        )
        vrow = result2.mappings().one()
        v = Vehicle.__new__(Vehicle)
        v.id = vrow["id"]
        v.vin = vrow.get("vin")
        v.display_name = vrow.get("display_name")
        v.provider = vrow.get("provider")
        v.provider_vehicle_id = vrow.get("provider_vehicle_id")
        v.nominal_battery_kwh = vrow.get("nominal_battery_kwh")
        return v

    # Insert new vehicle
    new_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO vehicles
                (id, provider, provider_vehicle_id, vin, display_name, nominal_battery_kwh,
                 timezone, created_at, updated_at)
            VALUES
                (:id, 'teslamate', :pvid, :vin, :name, :kwh, 'UTC', now(), now())
            ON CONFLICT (provider, provider_vehicle_id) DO NOTHING
            """
        ),
        {
            "id": str(new_id),
            "pvid": provider_vehicle_id,
            "vin": car.get("vin"),
            "name": car.get("name"),
            "kwh": 75.0,
        },
    )
    # Track in ImportMapping
    await db.execute(
        text(
            """
            INSERT INTO import_mappings
                (id, batch_id, source_table, source_id, target_table, target_id, action)
            VALUES
                (:id, :batch_id, 'cars', :src_id, 'vehicles', :tgt_id, 'created')
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "batch_id": str(batch.id),
            "src_id": str(car["id"]),
            "tgt_id": str(new_id),
        },
    )
    await db.commit()

    v = Vehicle.__new__(Vehicle)
    v.id = new_id
    v.vin = car.get("vin")
    v.display_name = car.get("name")
    v.provider = "teslamate"
    v.provider_vehicle_id = provider_vehicle_id
    v.nominal_battery_kwh = 75.0
    return v


# ---------------------------------------------------------------------------
# Snapshot bulk insert
# ---------------------------------------------------------------------------

async def _bulk_insert_snapshots(
    db: AsyncSession,
    vehicle: Vehicle,
    positions: list[dict],
    batch: ImportBatch,
    batch_size: int = 500,
) -> tuple[int, int]:
    """Insert positions as VehicleSnapshot rows in chunks.

    Returns (inserted_count, skipped_count).
    """
    inserted = 0
    skipped = 0

    for chunk_start in range(0, len(positions), batch_size):
        chunk = positions[chunk_start : chunk_start + batch_size]
        rows_to_track: list[dict] = []

        for pos in chunk:
            snap_id = uuid.uuid4()
            observed_at = _to_utc(pos.get("date"))
            if observed_at is None:
                skipped += 1
                continue

            result = await db.execute(
                text(
                    """
                    INSERT INTO vehicle_snapshots
                        (vehicle_id, observed_at, battery_level, usable_battery_level,
                         battery_range_km, speed_kmh, odometer_km, latitude, longitude,
                         charging_state, charger_power_kw, raw)
                    VALUES
                        (:vehicle_id, :observed_at, :battery_level, :usable_battery_level,
                         :battery_range_km, :speed_kmh, :odometer_km, :latitude, :longitude,
                         :charging_state, :charger_power_kw, :raw::jsonb)
                    ON CONFLICT (vehicle_id, observed_at) DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "vehicle_id": str(vehicle.id),
                    "observed_at": observed_at,
                    "battery_level": pos.get("battery_level"),
                    "usable_battery_level": pos.get("usable_battery_level"),
                    "battery_range_km": pos.get("rated_range_km"),
                    "speed_kmh": pos.get("speed"),
                    "odometer_km": pos.get("odometer"),
                    "latitude": pos.get("latitude"),
                    "longitude": pos.get("longitude"),
                    "charging_state": pos.get("charging_state"),
                    "charger_power_kw": pos.get("charger_power"),
                    "raw": '{"imported_from":"teslamate"}',
                },
            )
            row = result.one_or_none()
            if row is None:
                skipped += 1
            else:
                inserted += 1
                rows_to_track.append(
                    {
                        "id": str(uuid.uuid4()),
                        "batch_id": str(batch.id),
                        "source_table": "positions",
                        "source_id": observed_at.isoformat(),
                        "target_table": "vehicle_snapshots",
                        "target_id": str(row[0]),
                        "action": "created",
                    }
                )

        # Bulk insert mappings for this chunk
        if rows_to_track:
            await db.execute(
                text(
                    """
                    INSERT INTO import_mappings
                        (id, batch_id, source_table, source_id, target_table, target_id, action)
                    VALUES
                        (:id, :batch_id, :source_table, :source_id, :target_table, :target_id, :action)
                    """
                ),
                rows_to_track,
            )

        await db.commit()

    return inserted, skipped


# ---------------------------------------------------------------------------
# Charge session bulk insert
# ---------------------------------------------------------------------------

async def _bulk_insert_sessions(
    db: AsyncSession,
    vehicle: Vehicle,
    charging_processes: list[dict],
    batch: ImportBatch,
) -> tuple[int, int]:
    """Insert charging_processes as ChargeSession rows.

    Returns (inserted_count, skipped_count).
    """
    inserted = 0
    skipped = 0
    rows_to_track: list[dict] = []

    for cp in charging_processes:
        started_at = _to_utc(cp.get("start_date"))
        if started_at is None:
            skipped += 1
            continue

        result = await db.execute(
            text(
                """
                INSERT INTO charge_sessions
                    (id, vehicle_id, started_at, ended_at,
                     start_soc, end_soc, battery_kwh_added, cost_estimated,
                     imported_from, has_gap, incomplete, invalid)
                VALUES
                    (:id, :vehicle_id, :started_at, :ended_at,
                     :start_soc, :end_soc, :battery_kwh_added, :cost_estimated,
                     'teslamate', false, false, false)
                ON CONFLICT (vehicle_id, started_at) DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "vehicle_id": str(vehicle.id),
                "started_at": started_at,
                "ended_at": _to_utc(cp.get("end_date")),
                "start_soc": cp.get("start_battery_level"),
                "end_soc": cp.get("end_battery_level"),
                "battery_kwh_added": cp.get("charge_energy_added"),
                "cost_estimated": cp.get("cost"),
            },
        )
        row = result.one_or_none()
        if row is None:
            skipped += 1
        else:
            inserted += 1
            rows_to_track.append(
                {
                    "id": str(uuid.uuid4()),
                    "batch_id": str(batch.id),
                    "source_table": "charging_processes",
                    "source_id": str(cp["id"]),
                    "target_table": "charge_sessions",
                    "target_id": str(row[0]),
                    "action": "created",
                }
            )

    if rows_to_track:
        await db.execute(
            text(
                """
                INSERT INTO import_mappings
                    (id, batch_id, source_table, source_id, target_table, target_id, action)
                VALUES
                    (:id, :batch_id, :source_table, :source_id, :target_table, :target_id, :action)
                """
            ),
            rows_to_track,
        )

    await db.commit()
    return inserted, skipped


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

async def rollback_batch(db: AsyncSession, batch: ImportBatch) -> None:
    """Delete all records created by *batch* and mark it as rolled_back."""
    # Fetch all mappings for this batch
    result = await db.execute(
        text(
            "SELECT target_table, target_id FROM import_mappings WHERE batch_id = :batch_id"
        ),
        {"batch_id": str(batch.id)},
    )
    mappings = result.all()

    # Group by table for efficient deletion
    by_table: dict[str, list[str]] = {}
    for row in mappings:
        by_table.setdefault(row[0], []).append(row[1])

    # Delete from each table — order matters for FK constraints
    delete_order = ["vehicle_snapshots", "charge_sessions", "vehicles"]
    for table in delete_order:
        ids = by_table.get(table)
        if not ids:
            continue
        # Cast id type correctly: BigInteger for vehicle_snapshots, UUID for others
        if table == "vehicle_snapshots":
            await db.execute(
                text(f"DELETE FROM {table} WHERE id = ANY(:ids::bigint[])"),
                {"ids": ids},
            )
        else:
            await db.execute(
                text(f"DELETE FROM {table} WHERE id = ANY(:ids::uuid[])"),
                {"ids": ids},
            )

    # Remove mappings themselves
    await db.execute(
        text("DELETE FROM import_mappings WHERE batch_id = :batch_id"),
        {"batch_id": str(batch.id)},
    )

    batch.status = "rolled_back"
    batch.completed_at = datetime.now(timezone.utc)
    db.add(batch)
    await db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    return None
