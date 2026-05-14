"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-14

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("key_hash", sa.String(256), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )

    # ── vehicles ───────────────────────────────────────────────────────────────
    op.create_table(
        "vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("provider_vehicle_id", sa.String(256), nullable=False),
        sa.Column("vin", sa.String(17)),
        sa.Column("display_name", sa.String(256)),
        sa.Column("model", sa.String(128)),
        sa.Column("year", sa.Integer()),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("nominal_battery_kwh", sa.Numeric(6, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicles_provider_provider_vehicle_id", "vehicles", ["provider", "provider_vehicle_id"], unique=True)

    op.create_table(
        "vehicle_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("battery_level", sa.Numeric(5, 2)),
        sa.Column("usable_battery_level", sa.Numeric(5, 2)),
        sa.Column("battery_range_km", sa.Numeric(7, 2)),
        sa.Column("est_battery_range_km", sa.Numeric(7, 2)),
        sa.Column("ideal_battery_range_km", sa.Numeric(7, 2)),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("heading", sa.Integer()),
        sa.Column("speed_kmh", sa.Numeric(6, 2)),
        sa.Column("odometer_km", sa.Numeric(10, 2)),
        sa.Column("charging_state", sa.String(32)),
        sa.Column("charge_limit_soc", sa.Numeric(5, 2)),
        sa.Column("charger_power_kw", sa.Numeric(6, 2)),
        sa.Column("charger_voltage", sa.Integer()),
        sa.Column("charger_actual_current", sa.Integer()),
        sa.Column("charger_phases", sa.Integer()),
        sa.Column("plugged_in", sa.Boolean()),
        sa.Column("scheduled_charging_start", sa.DateTime(timezone=True)),
        sa.Column("inside_temp_c", sa.Numeric(4, 1)),
        sa.Column("outside_temp_c", sa.Numeric(4, 1)),
        sa.Column("climate_on", sa.Boolean()),
        sa.Column("is_preconditioning", sa.Boolean()),
        sa.Column("vehicle_state", sa.String(32)),
        sa.Column("sentry_mode", sa.Boolean()),
        sa.Column("locked", sa.Boolean()),
        sa.Column("is_user_present", sa.Boolean()),
        sa.Column("raw", postgresql.JSONB()),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_snapshots_vehicle_observed", "vehicle_snapshots", ["vehicle_id", "observed_at"])
    op.create_index("ix_snapshots_observed_brin", "vehicle_snapshots", ["observed_at"], postgresql_using="brin")

    op.create_table(
        "provider_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), server_default="info"),
        sa.Column("message", sa.Text()),
        sa.Column("raw", postgresql.JSONB()),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_provider_events_vehicle_occurred", "provider_events", ["vehicle_id", "occurred_at"])

    # ── locations ──────────────────────────────────────────────────────────────
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("location_type", sa.String(32), server_default="other"),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("radius_meters", sa.Integer(), server_default="100"),
        sa.Column("address", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── tariffs ────────────────────────────────────────────────────────────────
    op.create_table(
        "tariffs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("timezone", sa.String(64), server_default="UTC"),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "vehicle_tariff_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True)),
        sa.Column("tariff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("is_default", sa.Boolean(), server_default="false"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── charge sessions + plans ────────────────────────────────────────────────
    op.create_table(
        "charge_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True)),
        sa.Column("tariff_id", postgresql.UUID(as_uuid=True)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("start_soc", sa.Numeric(5, 2)),
        sa.Column("end_soc", sa.Numeric(5, 2)),
        sa.Column("charge_limit_soc", sa.Numeric(5, 2)),
        sa.Column("battery_kwh_added", sa.Numeric(8, 3)),
        sa.Column("wall_kwh_estimated", sa.Numeric(8, 3)),
        sa.Column("wall_kwh_actual", sa.Numeric(8, 3)),
        sa.Column("avg_power_kw", sa.Numeric(6, 2)),
        sa.Column("max_power_kw", sa.Numeric(6, 2)),
        sa.Column("avg_voltage", sa.Integer()),
        sa.Column("phases", sa.Integer()),
        sa.Column("charge_efficiency", sa.Numeric(5, 4)),
        sa.Column("cost_estimated", sa.Numeric(8, 4)),
        sa.Column("cost_currency", sa.String(3)),
        sa.Column("grid_kwh", sa.Numeric(8, 3)),
        sa.Column("solar_kwh", sa.Numeric(8, 3)),
        sa.Column("powerwall_kwh", sa.Numeric(8, 3)),
        sa.Column("energy_source", sa.String(16)),
        sa.Column("has_gap", sa.Boolean(), server_default="false"),
        sa.Column("incomplete", sa.Boolean(), server_default="false"),
        sa.Column("invalid", sa.Boolean(), server_default="false"),
        sa.Column("invalid_reason", sa.String(128)),
        sa.Column("imported_from", sa.String(32)),
        sa.Column("raw", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_charge_sessions_vehicle_started", "charge_sessions", ["vehicle_id", "started_at"])
    op.create_index("ix_charge_sessions_started_brin", "charge_sessions", ["started_at"], postgresql_using="brin")
    op.create_index("ix_charge_sessions_vehicle_started_unique", "charge_sessions", ["vehicle_id", "started_at"], unique=True)

    op.create_table(
        "charge_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tariff_id", postgresql.UUID(as_uuid=True)),
        sa.Column("session_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("departure_time", sa.DateTime(timezone=True)),
        sa.Column("current_soc", sa.Numeric(5, 2), nullable=False),
        sa.Column("target_soc", sa.Numeric(5, 2), nullable=False),
        sa.Column("recommended_start", sa.DateTime(timezone=True)),
        sa.Column("recommended_stop", sa.DateTime(timezone=True)),
        sa.Column("expected_kwh", sa.Numeric(8, 3)),
        sa.Column("expected_cost", sa.Numeric(8, 4)),
        sa.Column("expected_cost_currency", sa.String(3)),
        sa.Column("actual_kwh", sa.Numeric(8, 3)),
        sa.Column("actual_cost", sa.Numeric(8, 4)),
        sa.Column("actual_start", sa.DateTime(timezone=True)),
        sa.Column("actual_stop", sa.DateTime(timezone=True)),
        sa.Column("confidence", sa.String(16), server_default="moderate"),
        sa.Column("explanation", postgresql.ARRAY(sa.Text())),
        sa.Column("inputs", postgresql.JSONB()),
        sa.Column("result", postgresql.JSONB()),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["charge_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── battery estimates ──────────────────────────────────────────────────────
    op.create_table(
        "battery_estimates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("estimated_usable_kwh", sa.Numeric(6, 3), nullable=False),
        sa.Column("nominal_kwh", sa.Numeric(6, 3)),
        sa.Column("degradation_pct", sa.Numeric(5, 2)),
        sa.Column("confidence", sa.String(16), server_default="unknown"),
        sa.Column("sessions_used", sa.Integer(), server_default="0"),
        sa.Column("evidence", postgresql.JSONB()),
        sa.Column("explanation", postgresql.ARRAY(sa.Text())),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_battery_estimates_vehicle_calculated", "battery_estimates", ["vehicle_id", "calculated_at"])

    # ── alerts ─────────────────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), server_default="warning"),
        sa.Column("confidence", sa.String(16), server_default="moderate"),
        sa.Column("status", sa.String(16), server_default="open"),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.ARRAY(sa.Text())),
        sa.Column("possible_causes", postgresql.ARRAY(sa.Text())),
        sa.Column("recommended_actions", postgresql.ARRAY(sa.Text())),
        sa.Column("context", postgresql.JSONB()),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_vehicle_detected", "alerts", ["vehicle_id", "detected_at"])
    op.create_index("ix_alerts_status", "alerts", ["status"])

    # ── AI explanations ────────────────────────────────────────────────────────
    op.create_table(
        "ai_explanations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True)),
        sa.Column("asked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_question", sa.Text(), nullable=False),
        sa.Column("context_summary", postgresql.JSONB()),
        sa.Column("answer_markdown", sa.Text()),
        sa.Column("confidence", sa.String(16)),
        sa.Column("provider", sa.String(32)),
        sa.Column("model", sa.String(128)),
        sa.Column("prompt_tokens", sa.Integer()),
        sa.Column("completion_tokens", sa.Integer()),
        sa.Column("error", sa.Text()),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── import tracking ────────────────────────────────────────────────────────
    op.create_table(
        "import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(16), server_default="pending"),
        sa.Column("dry_run", sa.Boolean(), server_default="false"),
        sa.Column("summary", postgresql.JSONB()),
        sa.Column("error", sa.Text()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "import_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_table", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(256), nullable=False),
        sa.Column("target_table", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(256), nullable=False),
        sa.Column("action", sa.String(16), server_default="created"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── home energy ────────────────────────────────────────────────────────────
    op.create_table(
        "home_energy_samples",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("solar_kw", sa.Numeric(7, 3)),
        sa.Column("grid_import_kw", sa.Numeric(7, 3)),
        sa.Column("grid_export_kw", sa.Numeric(7, 3)),
        sa.Column("home_load_kw", sa.Numeric(7, 3)),
        sa.Column("charger_kw", sa.Numeric(7, 3)),
        sa.Column("battery_charge_kw", sa.Numeric(7, 3)),
        sa.Column("battery_soe_pct", sa.Numeric(5, 2)),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_home_energy_observed_brin", "home_energy_samples", ["observed_at"], postgresql_using="brin")
    op.create_index("ix_home_energy_source_observed", "home_energy_samples", ["source", "observed_at"])

    # ── integrations ───────────────────────────────────────────────────────────
    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("integration_type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true"),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("integrations")
    op.drop_table("home_energy_samples")
    op.drop_table("import_mappings")
    op.drop_table("import_batches")
    op.drop_table("ai_explanations")
    op.drop_table("alerts")
    op.drop_table("battery_estimates")
    op.drop_table("charge_plans")
    op.drop_table("charge_sessions")
    op.drop_table("vehicle_tariff_assignments")
    op.drop_table("tariffs")
    op.drop_table("locations")
    op.drop_table("provider_events")
    op.drop_table("vehicle_snapshots")
    op.drop_table("vehicles")
    op.drop_table("api_keys")
    op.drop_table("users")
