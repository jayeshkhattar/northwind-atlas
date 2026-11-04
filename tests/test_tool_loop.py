"""The generate → tool → generate loop."""
import json

import pytest

import src.agent as agent
from tests.conftest import message, tool_use

pytestmark = pytest.mark.anyio


async def test_tool_result_is_fed_back_and_grounds_the_answer(fake_llm, session):
    llm = fake_llm(
        classify=["TOOL"],
        generate=[message(tool_use("get_order_status", {"order_id": "NW-10001"})), "Order NW-10001 was delivered."],
        verify=["PASS"],
    )
    messages = await agent.run_agent(session, [], "Where is NW-10001?")

    assert session.calls == [("get_order_status", {"order_id": "NW-10001"})]
    tool_result = messages[2]["content"][0]
    assert tool_result["type"] == "tool_result" and tool_result["tool_use_id"] == "toolu_1"
    assert '"status": "delivered"' in tool_result["content"]
    assert '"status": "delivered"' in llm.calls_for("verify")[0]["messages"][0]["content"]


@pytest.mark.xfail(strict=True, reason="bug: tool_loop only answers the last tool_use block")
async def test_parallel_tool_calls_each_get_a_result(fake_llm, session):
    # Claude may return several tool_use blocks in one turn; the API rejects the next
    # request unless every one of them gets a tool_result.
    both = message(
        tool_use("get_order_status", {"order_id": "NW-10001"}, id="toolu_a"),
        tool_use("get_order_status", {"order_id": "NW-10002"}, id="toolu_b"),
    )
    fake_llm(classify=["TOOL"], generate=[both, "Both found."], verify=["PASS"])
    messages = await agent.run_agent(session, [], "Status of NW-10001 and NW-10002?")

    results = messages[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["toolu_a", "toolu_b"]
    assert json.loads(results[1]["content"])["order_id"] == "NW-10002"


def test_customer_ids_are_normalized():
    from src.tools import get_customer_orders, normalize_id
    assert normalize_id("cust 1", "CUST", 3) == "CUST-001"
    assert normalize_id("CUST-014", "CUST", 3) == "CUST-014"
    assert get_customer_orders("CUST-1") == get_customer_orders("CUST-001")
