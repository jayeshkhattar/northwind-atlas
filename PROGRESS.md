# Atlas — Build Progress
Project: Northwind support/ops agent. Learning mode (I write code, Claude reviews).

## Done
- Phase 0: env, repo, data generation (customers.json, orders.json)
- Phase 1: full RAG pipeline — chunking, BM25, embeddings (Voyage, cached), multi-index RRF fusion, stopwords, BM25 threshold guard
- Phase 1: agent loop + multiple tools (get_order_status, get_customer_orders) with dict dispatch
- Phase 1: unified agent — RAG context + tools in one call
- Conversation management: multi-turn memory + persistent JSON storage (load/save/display, auto-increment ids), survives restarts
- Evals: full harness — dataset (input/expected/grader shape), runner with per-case dispatch, code grader (case-insensitive substring, robust to en-dash traps), model grader (constrained one-word output, `startswith("PASS")` defensive parse). 6/6 on current cases.
- Hallucination fix — Atlas fabricated `support@northwind.com` and `1-800-NORTHWIND`. Verify KB is silent on these, tighten system prompt against fabrication, use existing phone-number eval case to measure before/after.

## Next
- Query routing (decide whether to retrieve vs always-retrieve; today RAG context is injected on every call including pure tool questions)
- Reranking (production-grade alternative to BM25 threshold guard)
- Split chat.py out of agent.py (display/orchestration separation)
- Phase 2: image + PDF intake
- Phase 3: MCP + orchestration (routing/chaining/parallelization)
- Phase 4/5: full eval pass, polish, README, demo script

## Backlog (noted, not yet built)
- Langfuse — trace/observe eval runs, capture pass-rate over time; add after first measured improvement so before/after story lands
- Expand eval coverage — multi-turn memory case, tool disambiguation (ambiguous "check my order"), retrieval failure case, non-determinism handling (run N times, average)
- Data generator realism (varied orders) — partially fixed

## Known limits (documented, not bugs)
- Substring grading has a variance floor — same code can flip pass/fail on identical case due to LLM non-determinism (observed on refund case)
- Threshold + stopwords tuned by eyeball, never measured — reranking backlog item addresses this# Atlas — Build Progress
Project: Northwind support/ops agent. Learning mode (I write code, Claude reviews).

## Done
- Phase 0: env, repo, data generation (customers.json, orders.json)
- Phase 1: full RAG pipeline — chunking, BM25, embeddings (Voyage, cached), multi-index RRF fusion, stopwords, BM25 threshold guard
- Phase 1: agent loop + multiple tools (get_order_status, get_customer_orders) with dict dispatch
- Phase 1: unified agent — RAG context + tools in one call
- Conversation management: multi-turn memory + persistent JSON storage (load/save/display, auto-increment ids), survives restarts
- Evals: full harness — dataset (input/expected/grader shape), runner with per-case dispatch, code grader (case-insensitive substring, robust to en-dash traps), model grader (constrained one-word output, `startswith("PASS")` defensive parse). 6/6 on current cases.

## Now
- Hallucination fix — Atlas fabricated `support@northwind.com` and `1-800-NORTHWIND`. Verify KB is silent on these, tighten system prompt against fabrication, use existing phone-number eval case to measure before/after.

## Next
- Query routing (decide whether to retrieve vs always-retrieve; today RAG context is injected on every call including pure tool questions)
- Reranking (production-grade alternative to BM25 threshold guard)
- Split chat.py out of agent.py (display/orchestration separation)
- Phase 2: image + PDF intake
- Phase 3: MCP + orchestration (routing/chaining/parallelization)
- Phase 4/5: full eval pass, polish, README, demo script

## Backlog (noted, not yet built)
- Langfuse — trace/observe eval runs, capture pass-rate over time; add after first measured improvement so before/after story lands
- Expand eval coverage — multi-turn memory case, tool disambiguation (ambiguous "check my order"), retrieval failure case, non-determinism handling (run N times, average)
- Data generator realism (varied orders) — partially fixed

## Known limits (documented, not bugs)
- Substring grading has a variance floor — same code can flip pass/fail on identical case due to LLM non-determinism (observed on refund case)
- Threshold + stopwords tuned by eyeball, never measured — reranking backlog item addresses this