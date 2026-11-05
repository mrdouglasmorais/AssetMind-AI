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


def test_skills_keep_the_engine_limits() -> None:
    text = {
        path.parent.name: path.read_text(encoding="utf-8")
        for path in SKILLS.glob("*/SKILL.md")
    }
    assert "zero model tokens" in text["orchestration"]
    assert "illustrative_assumption" in text["scenario-analysis"]
    assert "Monte Carlo" in text["scenario-analysis"]
    assert "DCF" in text["equity-analysis"]
    assert "Barsi" in text["equity-analysis"]
    assert "Buffett" in text["equity-analysis"]
    assert "Bazin" in text["equity-analysis"]
    assert "preço teto" in text["equity-analysis"]
    assert "Barsi" in text["real-estate-analysis"]
    assert "Baroni" in text["real-estate-analysis"]
    assert "Alden" in text["crypto-analysis"]
    assert "Antonopoulos" in text["crypto-analysis"]
    assert "Stock-to-flow" in text["crypto-analysis"]
    assert "news.google.com" in text["market-news"]
    assert "365" in text["crypto-analysis"]
    assert "tijolo" in text["real-estate-analysis"] or "brick" in text["real-estate-analysis"]
    assert "ignore previous instructions" in text["evidence-review"]
    assert "embedding" in text["token-balance"]
    schema = (SKILLS / "contracts" / "report.schema.json").read_text(encoding="utf-8")
    assert '"real_estate"' in schema
    assert "probabilidade" in schema
