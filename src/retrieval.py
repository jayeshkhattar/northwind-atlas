from pathlib import Path
from rank_bm25 import BM25Okapi
import numpy as np

def load_kb(kb_dir="data/kb"):
    chunks = []
    for path in Path(kb_dir).glob("*.md"):
        text = path.read_text()
        sections = text.split("## ")
        for section in sections[1:]:
            heading, body = section.split("\n", 1)
            chunks.append({"source":path.name, "heading": heading.strip(), "text": body.strip()})
    return chunks

def tokenize(text):
    return text.lower().split()

def build_tokens(chunks):
    tokenized_corpus = [tokenize(chunk["text"]) for chunk in chunks]
    return tokenized_corpus

def get_bm(tokens):
    bm25 = BM25Okapi(tokens)
    return bm25

def get_score(bm25, query):
    scores = bm25.get_scores(tokenize(query))
    return scores

def search(query, chunks, bm25, k=3):
    scores = get_score(bm25, query)
    top_indexes = np.argsort(scores)[::-1][:k]
    return [chunks[i] for i in top_indexes]

chunks = load_kb()
tokens = build_tokens(chunks)
bm25 = get_bm(tokens)
query = "how long do refunds take"
searchedChunks = search(query, chunks, bm25)
