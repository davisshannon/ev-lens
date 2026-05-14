import json

import httpx

from app.services.ai.base import AiProvider, ExplanationContext, ExplanationResult

_SYSTEM_PROMPT = """\
You are an EV intelligence assistant for EV Lens, a local-first Tesla monitoring platform.
You have access to factual vehicle data. Answer questions accurately based only on the provided context.
If the context doesn't contain enough information to answer confidently, say so.
Be concise and practical. Format responses in markdown with clear sections.\
"""

_DEFAULT_MODEL = "anthropic.claude-opus-4-7-20251101-v1:0"


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


class BedrockProvider(AiProvider):
    def __init__(
        self,
        aws_access_key: str,
        aws_secret_key: str,
        region: str = "us-east-1",
        model: str = _DEFAULT_MODEL,
    ) -> None:
        try:
            import boto3  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "boto3 is required for the Bedrock AI provider. "
                "Install it with: pip install boto3"
            ) from exc

        self._aws_access_key = aws_access_key
        self._aws_secret_key = aws_secret_key
        self._region = region
        self._model = model

    async def explain(self, question: str, context: ExplanationContext) -> ExplanationResult:
        import boto3
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        from botocore.credentials import Credentials

        url = (
            f"https://bedrock-runtime.{self._region}.amazonaws.com"
            f"/model/{self._model}/invoke"
        )

        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "system": _SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": _build_user_message(question, context)},
                ],
            }
        )

        credentials = Credentials(self._aws_access_key, self._aws_secret_key)
        aws_request = AWSRequest(method="POST", url=url, data=body)
        aws_request.headers["Content-Type"] = "application/json"
        SigV4Auth(credentials, "bedrock", self._region).add_auth(aws_request)

        signed_headers = dict(aws_request.headers)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=signed_headers, content=body)
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
        return "bedrock"
