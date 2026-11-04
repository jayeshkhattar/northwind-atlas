"""The grounding gate: pass, retry with the reason, then escalate."""
import pytest

import src.agent as agent
from src.agent import extract_reply

pytestmark = pytest.mark.anyio

FALLBACK = "Let me escalate you to a human agent"


@pytest.fixture(autouse=True)
def no_retrieval(monkeypatch):
    monkeypatch.setattr(agent, "build_context", lambda q: "Returns and refunds.md > Refund timing > Refunds are issued within 5 business days.")


async def test_grounded_answer_passes_first_time(fake_llm, session):
    llm = fake_llm(classify=["KB"], generate=["Refunds take 5 business days."], verify=["PASS"])
    signals = {}
    messages = await agent.run_agent(session, [], "How long do refunds take?", signals=signals)

    assert extract_reply(messages) == "Refunds take 5 business days."
    assert len(llm.calls_for("generate")) == 1
    assert signals["fallback"] is False


async def test_ungrounded_answer_retries_with_reason(fake_llm, session):
    llm = fake_llm(
        classify=["KB"],
        generate=["Refunds take 47 business days.", "Refunds take 5 business days."],
        verify=["FAIL: 47 days is not in the context", "PASS"],
    )
    signals = {}
    messages = await agent.run_agent(session, [], "How long do refunds take?", signals=signals)

    second = llm.calls_for("generate")[1]
    assert "Previous answer failed grounding: FAIL: 47 days is not in the context" in second["system"][-1]["text"]
    assert extract_reply(messages) == "Refunds take 5 business days."
    assert [v["passed"] for v in signals["verify"]] == [False, True]
    assert signals["fallback"] is False


async def test_max_retries_escalates_to_human(fake_llm, session):
    llm = fake_llm(classify=["KB"], generate=["Refunds need a blood sample."], verify=["FAIL: not in context"])
    signals = {}
    messages = await agent.run_agent(session, [], "Do refunds need a blood sample?", signals=signals)

    assert len(llm.calls_for("verify")) == 2
    assert FALLBACK in extract_reply(messages)
    assert signals["fallback"] is True


def test_verifier_sees_query_grounding_and_answer(fake_llm):
    llm = fake_llm(verify=["FAIL: price not in docs"])
    passed, reason = agent.verify("price?", "KB Context:\nnothing", "It costs $5")

    prompt = llm.calls_for("verify")[0]["messages"][0]["content"]
    assert "price?" in prompt and "KB Context:\nnothing" in prompt and "It costs $5" in prompt
    assert (passed, reason) == (False, "FAIL: price not in docs")
