"""BM25, semantic and fused retrieval against the real KB and cached vectors.
Query vectors are real Voyage embeddings recorded in tests/fixtures."""
import pytest

from src import search
from src.embeddings import semantic_search
from src.retrieval import load_kb, search_scored


def key(chunk):
    return (chunk["source"], chunk["heading"])


def test_kb_loads_in_a_stable_order():
    chunks = load_kb()
    assert len(chunks) == len(search.VECTORS) == 31
    assert [c["source"] for c in chunks] == sorted(c["source"] for c in chunks)


@pytest.mark.parametrize("query, expected", [
    ("how long do refunds take", ("Returns and refunds.md", "Refund timing")),
    ("my grinder makes a loud rattling noise", ("Grinder troubleshooting.md", "Grinder is loud or vibrating")),
    ("can I skip a month of beans", ("Bean subscription.md", "Managing your subscription")),
])
def test_bm25_top_hit(query, expected):
    (top, score), *_ = search_scored(query, search.CHUNKS, search.BM25, k=5)
    assert key(top) == expected
    assert score > 3


@pytest.mark.parametrize("query, expected", [
    ("how long do refunds take", ("Returns and refunds.md", "Refund timing")),
    ("Do you ship to Canada?", ("Shipping and delivery.md", "Delivery estimates")),
    ("my grinder makes a loud rattling noise", ("Grinder troubleshooting.md", "Grinder is loud or vibrating")),
])
def test_semantic_top_hit(query, expected):
    assert key(semantic_search(query, search.CHUNKS, search.VECTORS, k=5)[0]) == expected


def test_semantic_finds_paraphrase_bm25_misses():
    # No word overlap with the refunds article; this is why the embedding index exists.
    query = "how do I get my money back"
    assert all(score == 0 for _, score in search_scored(query, search.CHUNKS, search.BM25, k=5))
    top3 = semantic_search(query, search.CHUNKS, search.VECTORS, k=3)
    assert {c["source"] for c in top3} == {"Returns and refunds.md"}


def test_rrf_scores_and_order_are_deterministic():
    a = {"source": "a.md", "heading": "A", "text": ""}
    b = {"source": "b.md", "heading": "B", "text": ""}
    c = {"source": "c.md", "heading": "C", "text": ""}
    scores = search.reciprocal_rank_fusion([a, b], [b, c])

    assert scores[("b.md", "B")] == pytest.approx(1 / 61 + 1 / 60)
    assert scores[("a.md", "A")] == pytest.approx(1 / 60)
    assert scores[("c.md", "C")] == pytest.approx(1 / 61)
    ranked = sorted(scores, key=scores.get, reverse=True)
    assert ranked == [("b.md", "B"), ("a.md", "A"), ("c.md", "C")]
    again = search.reciprocal_rank_fusion([a, b], [b, c])
    assert sorted(again, key=again.get, reverse=True) == ranked


def test_fused_search_drops_weak_bm25_hits():
    # Gibberish gets BM25 score 0 everywhere, so only semantic hits reach fusion.
    query = "zxqv plorb"
    fused = search.multi_index_search_score(query, k=3)
    semantic = semantic_search(query, search.CHUNKS, search.VECTORS, k=3)
    assert [key(c) for c in fused] == [key(c) for c in semantic]
