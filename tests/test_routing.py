"""The router decides whether retrieval runs. Tools are offered on every route."""
import pytest

import src.agent as agent

pytestmark = pytest.mark.anyio


@pytest.fixture
def spy_retrieval(monkeypatch):
    calls = []

    def fake_build_context(query):
        calls.append(query)
        return "Returns and refunds.md > Refund timing > Refunds are issued within 5 business days."

    monkeypatch.setattr(agent, "build_context", fake_build_context)
    return calls


def system_text(kwargs):
    return "\n".join(block["text"] for block in kwargs["system"])


@pytest.mark.parametrize("label, retrieves", [("KB", True), ("BOTH", True), ("TOOL", False)])
async def test_each_route_controls_retrieval(fake_llm, session, spy_retrieval, label, retrieves):
    llm = fake_llm(classify=[label], generate=["ok"], verify=["PASS"])
    await agent.run_agent(session, [], "how long do refunds take?")

    assert bool(spy_retrieval) is retrieves
    generate = llm.calls_for("generate")[0]
    assert ("Relevant documentation" in system_text(generate)) is retrieves
    assert {t["name"] for t in generate["tools"]} == {"get_order_status", "get_customer_orders"}


def test_classifier_output_is_normalized(fake_llm):
    fake_llm(classify=["  kb\n"])
    assert agent.classify_llm("do you ship to Canada?") == "KB"


async def test_unrecognized_label_falls_back_to_tools_only(fake_llm, session, spy_retrieval):
    # A chatty or unexpected router reply must not crash the turn. It is treated
    # like TOOL: no retrieval, tools still offered, and the verify gate still runs.
    llm = fake_llm(classify=["I think this is about refunds"], generate=["ok"], verify=["PASS"])
    signals = {}
    await agent.run_agent(session, [], "refunds?", signals=signals)

    assert spy_retrieval == []
    assert llm.calls_for("generate")[0]["tools"]
    assert signals["verify"] == [{"attempt": 1, "passed": True, "reason": ""}]
