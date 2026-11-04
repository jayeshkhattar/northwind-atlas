"""What goes into the prompt: size and provenance of the retrieved context."""
import pytest

import src.agent as agent
from src import search

pytestmark = pytest.mark.anyio

# Budget for the retrieved-docs block. Three chunks of this KB run ~200 tokens; the
# budget leaves room for longer articles but catches a top-k or chunking change that
# would quietly multiply prompt cost.
CONTEXT_TOKEN_BUDGET = 1_000
SYSTEM_TOKEN_BUDGET = 1_500
QUERIES = [
    "How long do refunds take?",
    "Do you ship to Canada?",
    "What's your customer support phone number?",
    "Do you offer student discounts?",
    "my grinder makes a loud rattling noise",
]


def approx_tokens(text):
    return len(text) / 4  # close enough for English; the real count is in the trace


@pytest.mark.parametrize("query", QUERIES)
def test_context_stays_under_budget(query):
    assert approx_tokens(agent.build_context(query)) < CONTEXT_TOKEN_BUDGET


async def test_full_system_prompt_stays_under_budget(fake_llm, session):
    llm = fake_llm(classify=["BOTH"], generate=["ok"], verify=["PASS"])
    await agent.run_agent(session, [], "How long do refunds take?")
    system = "\n".join(b["text"] for b in llm.calls_for("generate")[0]["system"])
    assert approx_tokens(system) < SYSTEM_TOKEN_BUDGET


@pytest.mark.parametrize("query", QUERIES)
def test_every_context_block_cites_a_retrieved_chunk(query):
    retrieved = search.multi_index_search_score(query)
    context = agent.build_context(query)
    known = {(c["source"], c["heading"]): c["text"] for c in search.CHUNKS}

    assert len(retrieved) == 3
    position = 0
    for chunk in retrieved:
        citation = f"{chunk['source']} > {chunk['heading']} > "
        assert known[(chunk["source"], chunk["heading"])] == chunk["text"]
        found = context.find(citation + chunk["text"], position)
        assert found >= position, f"{citation} missing or out of rank order"
        position = found + len(citation)
    # nothing in the context that wasn't retrieved
    assert len(context) == sum(len(f"{c['source']} > {c['heading']} > {c['text']}") for c in retrieved) + 2 * (len(retrieved) - 1)
