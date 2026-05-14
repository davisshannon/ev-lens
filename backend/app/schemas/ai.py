from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AiExplainRequest(BaseModel):
    vehicle_id: UUID
    question: str
    question_type: str = "general"


class AiExplanationOut(BaseModel):
    id: UUID
    vehicle_id: UUID | None
    asked_at: datetime
    user_question: str
    answer_markdown: str | None
    confidence: str | None
    provider: str | None
    model: str | None
    error: str | None

    model_config = {"from_attributes": True}
