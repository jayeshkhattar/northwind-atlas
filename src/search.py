from src.embeddings import semantic_search, get_vectors
from src.retrieval import load_kb, build_tokens, get_bm, search, search_scored
from src.tracing import span, set_attrs

CHUNKS = load_kb()
TOKENS = build_tokens(CHUNKS)
BM25 = get_bm(TOKENS)
VECTORS = get_vectors(CHUNKS)

def reciprocal_rank_fusion(bm25_hits, semantic_hits, k=60):
    scores = {}
    for rank, chunk in enumerate(bm25_hits):
        key = (chunk["source"], chunk["heading"])
        scores[key] = scores.get(key, 0) + 1/(k + rank)
    for rank, chunk in enumerate(semantic_hits):
        key = (chunk["source"], chunk["heading"])
        scores[key] = scores.get(key, 0) + 1 / (k + rank)
    return scores

#multi index search without score
def multi_index_search(query, k=3):    
    bm25_hits = search(query, CHUNKS, BM25, 5)
    semantic_hits = semantic_search(query, CHUNKS, VECTORS, 5)
    scores = reciprocal_rank_fusion(bm25_hits, semantic_hits)

    ranked_keys = sorted(scores, key=scores.get, reverse=True)[:k]
    results = []
    for source, heading in ranked_keys:
        for chunk in CHUNKS:
            if chunk["source"] == source and chunk["heading"] == heading:
                results.append(chunk)
                break
    return results

#multi index search with bm25 score
def multi_index_search_score(query, k=3, bm25_min=1.0):    
    with span("retrieval", kind="retriever", **{"retrieval.query": query, "retrieval.top_k": k, "retrieval.bm25_min": bm25_min}) as s:
        scored = search_scored(query, CHUNKS, BM25, 5)
        bm25_hits = [chunk for chunk, score in scored if score >= bm25_min]

        semantic_hits = semantic_search(query, CHUNKS, VECTORS, 5)
        scores = reciprocal_rank_fusion(bm25_hits, semantic_hits)

        ranked_keys = sorted(scores, key=scores.get, reverse=True)[:k]
        results = []
        for source, heading in ranked_keys:
            for chunk in CHUNKS:
                if chunk["source"] == source and chunk["heading"] == heading:
                    results.append(chunk)
                    break
        set_attrs(s, **{
            "retrieval.bm25": [{"chunk": f"{c['source']} > {c['heading']}", "score": round(float(sc), 3)} for c, sc in scored],
            "retrieval.bm25_kept": len(bm25_hits),
            "retrieval.semantic": [f"{c['source']} > {c['heading']}" for c in semantic_hits],
            "retrieval.fused": [{"rank": i + 1, "chunk": f"{src} > {h}", "rrf": round(scores[(src, h)], 5)} for i, (src, h) in enumerate(ranked_keys)],
        })
    return results



#query = "how do I get my money back"
query = "how long do refunds take"

#results = multi_index_search(query)
results = multi_index_search_score(query)
