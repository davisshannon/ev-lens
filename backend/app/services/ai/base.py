from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExplanationContext:
    """Deterministically assembled context from DB — no hallucination possible."""
    vehicle_id: str
    question_type: str  # e.g. "vampire_drain", "slow_charge", "battery_health"
    time_window_hours: int = 48
    charge_sessions: list[dict[str, Any]] = field(default_factory=list)
    battery_estimates: list[dict[str, Any]] = field(default_factory=list)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    snapshots_summary: dict[str, Any] = field(default_factory=dict)
    tariff_info: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExplanationResult:
    answer_markdown: str
    confidence: str  # low/moderate/high
    evidence: list[str]
    next_steps: list[str]
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    error: str | None = None


class AiProvider(ABC):
    """Pluggable AI provider interface. Implementations: Anthropic, OpenAI, xAI, Bedrock."""

    @abstractmethod
    async def explain(self, question: str, context: ExplanationContext) -> ExplanationResult: ...

    @abstractmethod
    def provider_name(self) -> str: ...
