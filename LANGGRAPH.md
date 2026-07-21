# Hand-rolled vs LangGraph

Hand-rolled, the whole agent lived in one method — classify, retrieve, generate, verify, retry all tangled together. It worked, but it was messy to change.

LangGraph forced node boundaries. Nodes are independent, so I can reuse them, rewire edges, and compose multiple graphs from the same pieces.

The retry was the clearest win: it lives in one conditional edge, not smeared through generate and verify. I can change retry policy without touching either node.

Honest limit: my tool-calling loop still sits imperatively inside the generate node — the graph can't express it.