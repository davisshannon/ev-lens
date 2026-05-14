import json

import httpx

from app.services.ai.base import AiProvider, ExplanationContext, ExplanationResult

_SYSTEM_PROMPT = """\
You are an EV intelligence assistant for EV Lens, a local-first Tesla monitoring platform.
You have access to factual vehicle data. Answer questions accurately based only on the provided context.
If the context doesn't contain enough information to answer confidently, say so.
Be concise and practical. Format responses in markdown with clear sections.\
"""


def _build_user_message(question: str, context: ExplanationContext) -> str:
    parts = [
        f"**Question type:** {context.question_type}",
        f"**Vehicle ID:** {context.vehicle_id}",
        f"**Time window:** last {context.time_window_hours} hours",
    ]

    if context.charge_sessions:
        parts.append("\n**Recent charge sessions:**")
        parts.append(json.dumps(context.charge_sessions, indent=2, default=str))

    if context.battery_estimates:
        parts.append("\n**Battery estimates:**")
        parts.append(json.dumps(context.battery_estimates, indent=2, default=str))

    if context.alerts:
        parts.append("\n**Open alerts:**")
        parts.append(json.dumps(context.alerts, indent=2, default=str))

    if context.snapshots_summary:
        parts.append("\n**Snapshots summary:**")
        parts.append(json.dumps(context.snapshots_summary, indent=2, default=str))

    if context.tariff_info:
        parts.append("\n**Tariff info:**")
        parts.append(json.dumps(context.tariff_info, indent=2, default=str))

    parts.append(f"\n**User question:** {question}")
    return "\n".join(parts)


class AnthropicProvider(AiProvider):
    def __init__(self, api_key: str, model: str = "claude-opus-4-7") -> None:
        self._api_key = api_key
        self._model = model

    async def explain(self, question: str, context: ExplanationContext) -> ExplanationResult:
        payload = {
            "model": self._model,
            "max_tokens": 1024,
            "system": _SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": _build_user_message(question, context)},
            ],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        answer = data["content"][0]["text"]
        input_tokens: int = data["usage"]["input_tokens"]
        output_tokens: int = data["usage"]["output_tokens"]

        return ExplanationResult(
            answer_markdown=answer,
            confidence="moderate",
            evidence=[],
            next_steps=[],
            provider=self.provider_name(),
            model=self._model,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        )

    def provider_name(self) -> str:
        return "anthropic"
