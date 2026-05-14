import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AiExplanation(Base):
    __tablename__ = "ai_explanations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"))
    asked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user_question: Mapped[str] = mapped_column(Text, nullable=False)
    context_summary: Mapped[dict | None] = mapped_column(JSONB)

    answer_markdown: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(String(16))  # low/moderate/high

    provider: Mapped[str | None] = mapped_column(String(32))   # anthropic/openai/xai/bedrock
    model: Mapped[str | None] = mapped_column(String(128))
    prompt_tokens: Mapped[int | None]
    completion_tokens: Mapped[int | None]

    error: Mapped[str | None] = mapped_column(Text)
