from app.config import settings
from app.services.ai.base import AiProvider


def get_ai_provider() -> AiProvider | None:
    """Returns configured AI provider based on settings, or None if not configured.

    Priority order: anthropic -> openai -> xai -> bedrock.
    Returns the first provider whose credentials are set in settings.
    """
    model_override = settings.ai_model_override or None

    if settings.anthropic_api_key:
        from app.services.ai.anthropic_provider import AnthropicProvider

        kwargs: dict = {"api_key": settings.anthropic_api_key}
        if model_override:
            kwargs["model"] = model_override
        return AnthropicProvider(**kwargs)

    if settings.openai_api_key:
        from app.services.ai.openai_provider import OpenAIProvider

        kwargs = {"api_key": settings.openai_api_key}
        if model_override:
            kwargs["model"] = model_override
        return OpenAIProvider(**kwargs)

    if settings.xai_api_key:
        from app.services.ai.xai_provider import XAIProvider

        kwargs = {"api_key": settings.xai_api_key}
        if model_override:
            kwargs["model"] = model_override
        return XAIProvider(**kwargs)

    if settings.aws_access_key_id and settings.aws_secret_access_key:
        from app.services.ai.bedrock_provider import BedrockProvider

        kwargs = {
            "aws_access_key": settings.aws_access_key_id,
            "aws_secret_key": settings.aws_secret_access_key,
            "region": settings.aws_region,
        }
        if model_override:
            kwargs["model"] = model_override
        return BedrockProvider(**kwargs)

    return None
