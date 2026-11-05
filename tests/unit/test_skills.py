from pathlib import Path

from assetmind.agents.factory import build_report_agent, build_specialist_agents, load_skill_index

SKILLS = Path(__file__).resolve().parents[2] / "skills"


def test_runtime_skills_load_without_a_model_call() -> None:
    names = load_skill_index(str(SKILLS))
    assert {item.split(":", 1)[0] for item in names} == {
        "equity-analysis",
        "crypto-analysis",
        "real-estate-analysis",
        "scenario-analysis",
        "evidence-review",
        "orchestration",
        "token-balance",
        "market-news",
    }
    report = build_report_agent(
        model_id="openai/gpt-test",
        api_key="test-key",
        max_tokens=200,
        skills_dir=str(SKILLS),
    )
    specialists = build_specialist_agents(model_id="openai/gpt-test", api_key="test-key", max_tokens=200)
    assert report.tools == []
    assert [agent.name for agent in specialists] == [
        "Equity Analyst",
        "Crypto Analyst",
        "Real Estate Analyst",
        "Evidence Validator",
    ]
    assert all(agent.tools == [] for agent in specialists)
