import json
import os
import voyageai
from dotenv import load_dotenv
import numpy as np

from src.retrieval import load_kb
from src.tracing import span, set_attrs

load_dotenv()
vo = voyageai.Client()

VECTOR_CACHE = "data/vectors.json"


def embed_chunks(chunks):
    texts = [chunk["text"] for chunk in chunks]
    result = vo.embed(texts, model="voyage-3.5-lite")
    return result.embeddings


def get_vectors(chunks):
    if os.path.exists(VECTOR_CACHE):
        with open(VECTOR_CACHE) as f:
            return json.load(f)

    vectors = embed_chunks(chunks)
    with open(VECTOR_CACHE, "w") as f:
        json.dump(vectors, f)
    return vectors


def semantic_search(query, chunks, vectors, k=5):
    with span("embedding.query", kind="embedding", **{"embedding.model": "voyage-3.5-lite"}) as s:
        query_vec = vo.embed([query], model="voyage-3.5-lite").embeddings[0]

        sims = np.dot(vectors, query_vec) / (
            np.linalg.norm(vectors, axis=1) * np.linalg.norm(query_vec)
        )

        top_indexes = np.argsort(sims)[::-1][:k]
        set_attrs(s, **{"embedding.top_scores": [round(float(sims[i]), 4) for i in top_indexes]})
    return [chunks[i] for i in top_indexes]


if __name__ == "__main__":
    chunks = load_kb()
    vectors = get_vectors(chunks)
    for hit in semantic_search("how do I get my money back", chunks, vectors):
        print(hit["source"], "→", hit["heading"])