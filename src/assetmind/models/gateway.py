"""Model gateway. Construction stores credentials and does not call the network."""

from agno.models.groq import Groq
from agno.models.openrouter import OpenRouter

from assetmind.config.settings import Settings


def build_groq(*, model_id: str, api_key: str, max_tokens: int) -> Groq:
    if not model_id or not api_key:
        raise ValueError("Groq requires a model id and an API key.")
    return Groq(id=model_id, api_key=api_key, max_tokens=max_tokens, temperature=0.2)


def build_openrouter(*, model_id: str, api_key: str, max_tokens: int) -> OpenRouter:
    if not model_id or not api_key:
        raise ValueError("OpenRouter requires a model id and an API key.")
    return OpenRouter(id=model_id, api_key=api_key, max_tokens=max_tokens)


def build_llm(settings: Settings, *, max_tokens: int) -> Groq | OpenRouter:
    if settings.llm_provider == "groq":
        return build_groq(
            model_id=settings.groq_model,
            api_key=settings.groq_api_key or "",
            max_tokens=max_tokens,
        )
    return build_openrouter(
        model_id=settings.openrouter_model,
        api_key=settings.openrouter_api_key or "",
        max_tokens=max_tokens,
    )
