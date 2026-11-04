"""Re-record the query embeddings the offline tests use (needs VOYAGE_API_KEY).

    python -m tests.fixtures.record_query_vectors
"""
import json
from pathlib import Path

import voyageai
from dotenv import load_dotenv

QUERIES = [
    "how long do refunds take",
    "How long do refunds take?",
    "how do I get my money back",
    "my espresso shot runs really fast and tastes watery",
    "can I skip a month of beans",
    "my grinder makes a loud rattling noise",
    "Do you ship to Canada?",
    "What's your customer support phone number?",
    "Do you offer student discounts?",
    "zxqv plorb",
]

if __name__ == "__main__":
    load_dotenv(".env")
    vectors = voyageai.Client().embed(QUERIES, model="voyage-3.5-lite").embeddings
    out = Path(__file__).with_name("query_vectors.json")
    out.write_text(json.dumps(dict(zip(QUERIES, vectors))))
    print(f"wrote {len(QUERIES)} vectors to {out}")
