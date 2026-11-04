"""OpenRouter model gateway. Construction does not call the network."""

from agno.models.openrouter import OpenRouter


def build_openrouter(*, model_id: str, api_key: str, max_tokens: int) -> OpenRouter:
    if not model_id or not api_key:
        raise ValueError("OpenRouter requires a model id and an API key.")
    return OpenRouter(id=model_id, api_key=api_key, max_tokens=max_tokens)
