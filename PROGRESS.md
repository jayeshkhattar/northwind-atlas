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
- Hallucination fix — Atlas fabricated `support@northwind.com` and `1-800-NORTHWIND`. Verify KB is silent on these, tighten system prompt against fabrication, use existing phone-number eval case to measure before/after.
- Query routing (decide whether to retrieve vs always-retrieve; today RAG context is injected on every call including pure tool questions)
- Multimodal intake — image + PDF via load_file_block (base64 blocks; image→"image", PDF→"document", ext-driven media_type, raises on unsupported types). Wired into run_agent via optional image_path param; text callers unaffected. Verified live: Claude read a PNG and a PDF end to end.
- Verify node — post-answer checkpoint. LLM call judges whether the drafted answer is grounded in real KB context + tool results (not the prompt/schemas). Returns bool. Verified both ways: True on grounded answers and honest refusals, False on unsupported claims. First node of the orchestration chain.

## Next
- Reranking (production-grade alternative to BM25 threshold guard)
- Split chat.py out of agent.py (display/orchestration separation)
- Phase 3: MCP + orchestration (routing/chaining/parallelization)
- Phase 4/5: full eval pass, polish, README, demo script

## Backlog (noted, not yet built)
- Langfuse — trace/observe eval runs, capture pass-rate over time; add after first measured improvement so before/after story lands
- Expand eval coverage — multi-turn memory case, tool disambiguation (ambiguous "check my order"), retrieval failure case, non-determinism handling (run N times, average)
- Data generator realism (varied orders) — partially fixed
- Attachment token optimization (FDE cost tuning) — reduce tokens spent on image/PDF intake:
  - Downscale images before base64 (Claude tokenizes by dimensions; ~1000–1500px long edge keeps text legible at 2–4× lower cost). Pillow resize in load_file_block.
  - Text-based PDFs → extract text (pdfplumber) and send as text block instead of document block; reserve document-vision path for scanned/layout-critical PDFs.
  - Multi-turn: send file once, don't resend; add prompt caching on file-heavy prefix; optional summarize-and-drop for long convos.
  - Principle: optimize the encoding (resolution/format), not the content — you can't know what's "unnecessary" in a file before the model reads it.

## Known limits (documented, not bugs)
- Substring grading has a variance floor — same code can flip pass/fail on identical case due to LLM non-determinism (observed on refund case)
- Threshold + stopwords tuned by eyeball, never measured — reranking backlog item addresses this