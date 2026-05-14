from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class HomeEnergySample(Base):
    __tablename__ = "home_energy_samples"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # wall_connector/powerwall/home_assistant/manual

    solar_kw: Mapped[float | None] = mapped_column(Numeric(7, 3))
    grid_import_kw: Mapped[float | None] = mapped_column(Numeric(7, 3))
    grid_export_kw: Mapped[float | None] = mapped_column(Numeric(7, 3))
    home_load_kw: Mapped[float | None] = mapped_column(Numeric(7, 3))
    charger_kw: Mapped[float | None] = mapped_column(Numeric(7, 3))
    battery_charge_kw: Mapped[float | None] = mapped_column(Numeric(7, 3))  # positive=charging, negative=discharging
    battery_soe_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))  # Powerwall state of energy

    __table_args__ = (
        Index("ix_home_energy_observed_brin", "observed_at", postgresql_using="brin"),
        Index("ix_home_energy_source_observed", "source", "observed_at"),
    )
