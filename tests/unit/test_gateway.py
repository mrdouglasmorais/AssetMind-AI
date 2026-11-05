from agno.models.groq import Groq

from assetmind.agents.chat import build_chat_agent
from assetmind.agents.report_model import ReportModel
from assetmind.config.settings import Settings
from assetmind.models.gateway import build_groq


def test_groq_gateway_stores_credentials_without_a_network_call() -> None:
    model = build_groq(model_id="openai/gpt-oss-120b", api_key="test-key", max_tokens=120)
    assert isinstance(model, Groq)
    assert model.id == "openai/gpt-oss-120b"
    assert model.api_key == "test-key"
    assert model.max_tokens == 120
    assert model.client is None


def test_chat_agent_uses_groq_when_the_key_is_configured() -> None:
    settings = Settings(
        api_key="local-dev-key",
        llm_provider="groq",
        groq_api_key="test-key",
        groq_model="openai/gpt-oss-120b",
    )
    agent = build_chat_agent(service=None, settings=settings)  # type: ignore[arg-type]
    assert isinstance(agent.model, Groq)
    assert agent.model.id == "openai/gpt-oss-120b"
    assert len(agent.tools) == 4
    assert agent.pre_hooks is not None
    assert agent.post_hooks is not None


def test_chat_agent_stays_deterministic_without_a_groq_key() -> None:
    settings = Settings(api_key="local-dev-key", llm_provider="groq", groq_api_key="")
    agent = build_chat_agent(service=None, settings=settings)  # type: ignore[arg-type]
    assert isinstance(agent.model, ReportModel)
    assert agent.tools == []
