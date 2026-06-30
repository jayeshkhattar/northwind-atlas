from src.embeddings import semantic_search, get_vectors
from src.retrieval import load_kb, build_tokens, get_bm, search, search_scored

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
    scored = search_scored(query, CHUNKS, BM25, 5)
    bm25_hits = [chunk for chunk, score in scored if score >= bm25_min]
    print("scores:", [round(s, 2) for s in [score for chunk, score in scored]])
    print("bm25 kept:", len(bm25_hits))

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



#query = "how do I get my money back"
query = "how long do refunds take"

#results = multi_index_search(query)
results = multi_index_search_score(query)

for hit in results:
    print(hit["source"], "→", hit["heading"])