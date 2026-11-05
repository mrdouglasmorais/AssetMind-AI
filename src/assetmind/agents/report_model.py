"""Model stand-in that returns a prepared report and does not call a provider."""

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass, field

from agno.models.base import Model
from agno.models.response import ModelResponse


@dataclass
class ReportModel(Model):
    """Satisfies the Agno model interface with a local async runner."""

    id: str = "assetmind-deterministic"
    name: str = "AssetMind"
    provider: str = "assetmind"
    runner: Callable[[str], Awaitable[str]] | None = field(default=None, repr=False)

    def invoke(self, *args: object, **kwargs: object) -> ModelResponse:
        return ModelResponse(role="assistant", content="The analyst answers on the async chat path.")

    async def ainvoke(self, *args: object, **kwargs: object) -> ModelResponse:
        return ModelResponse(role="assistant", content=await self._answer(kwargs.get("messages")))

    def invoke_stream(self, *args: object, **kwargs: object) -> Iterator[ModelResponse]:
        yield self.invoke(*args, **kwargs)

    async def ainvoke_stream(self, *args: object, **kwargs: object) -> AsyncIterator[ModelResponse]:
        yield ModelResponse(role="assistant", content=await self._answer(kwargs.get("messages")))

    def _parse_provider_response(self, response: object, **kwargs: object) -> ModelResponse:
        return ModelResponse(role="assistant", content=str(response))

    def _parse_provider_response_delta(self, response: object) -> ModelResponse:
        return ModelResponse(role="assistant", content=str(response))

    async def _answer(self, messages: object) -> str:
        if self.runner is None:
            return "The analyst is not configured."
        return await self.runner(_latest_user_text(messages))


def _latest_user_text(messages: object) -> str:
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if getattr(message, "role", None) != "user":
            continue
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content
    return ""
