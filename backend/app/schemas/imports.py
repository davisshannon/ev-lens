from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ImportBatchOut(BaseModel):
    id: UUID
    source_type: str
    started_at: datetime
    completed_at: datetime | None
    status: str
    dry_run: bool
    summary: dict | None
    error: str | None

    model_config = {"from_attributes": True}


class TeslamateImportRequest(BaseModel):
    db_url: str
    vehicle_id: UUID | None = None
