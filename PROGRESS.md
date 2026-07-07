# Atlas — Build Progress
Project: Northwind support/ops agent. Learning mode (I write code, Claude reviews).

## Done
- Phase 0: env, repo, data generation (customers.json, orders.json)
- Phase 1: full RAG pipeline — chunking, BM25, embeddings (Voyage, cached), multi-index RRF fusion, stopwords, BM25 threshold guard
- Phase 1: agent loop + multiple tools (get_order_status, get_customer_orders) with dict dispatch
- Phase 1: unified agent — RAG context + tools in one call
- Conversation management: multi-turn memory + persistent JSON storage (load/save/display, auto-increment ids), survives restarts
- Evals: full harness — dataset (input/expected/grader shape), runner with per-case dispatch, code grader (case-insensitive substring, robust to en-dash traps), model grader (constrained one-word output, `startswith("PASS")` defensive parse). 6/6 on current cases.
- Hallucination fix — Atlas fabricated support email + phone in the escalation path. Root cause: prompt said "don't invent policies" but a phone number isn't a policy. Fix: generalized the no-fabrication rule with explicit high-risk categories (contact details, policies, prices). Verified 6/6 evals + clean escalation path. Eval-driven: red → prompt change → green.
- Query routing — v1 regex (NW-/CUST- patterns) → v2 LLM classifier (KB/TOOL/BOTH intent). LLM router removes ID-pattern brittleness: classifies by intent, scales to new tables/ID formats without new regex. Tools always-on regardless of route (router gates retrieval, not tool access — a misroute degrades gracefully). Verified 6/6 evals.
- Multimodal intake — image + PDF via load_file_block (base64 blocks; image→"image", PDF→"document", ext-driven media_type, raises on unsupported types). Wired into run_agent via optional file_path param; text callers unaffected. Verified live: Claude read a PNG and a PDF end to end.
- Orchestration chain (verify node) — classify → generate_answer (tool loop, extracted as own fn) → verify (grounding gate: judges answer against real KB context + tool results, returns verdict + reason) → retry-with-reason (max 2 attempts, failure reason injected into system prompt) → safe fallback (replaces unverified answer with escalation message after 2 fails). Untangled nested tool/retry loops via extraction. Full 6/6 eval suite passes through the new chain; caught a real UnboundLocalError (misplaced return in tool loop) during refactor — evals-first paid off.

## Next
- Cleanup pass — dead code (classify regex, send_to_claude), duplicated extract_reply (agent.py + evals.py), debug prints ([route:], [verify:]), split chat.py out of agent.py
- Reranking (production-grade alternative to BM25 threshold guard)
- Multi-agent contrast exercise — orchestrator + specialists, measured against the chain; document why chain wins (or doesn't)
- Phase 3: MCP (wrap tools as server, agent as client)
- Phase 4/5: polish, README, demo script

## Backlog (noted, not yet built)
- Langfuse — trace/observe eval runs, capture pass-rate over time; add after first measured improvement so before/after story lands
- Expand eval coverage — multi-turn memory case, tool disambiguation (ambiguous "check my order"), retrieval failure case, non-determinism handling (run N times, average)
- Data generator realism (varied orders) — partially fixed
- Attachment token optimization (FDE cost tuning):
  - Downscale images before base64 (Claude tokenizes by dimensions; ~1000–1500px long edge keeps text legible at 2–4× lower cost). Pillow resize in load_file_block.
  - Text-based PDFs → extract text (pdfplumber), send as text block; reserve document-vision path for scanned/layout-critical PDFs.
  - Multi-turn: send file once, don't resend; prompt caching on file-heavy prefix; optional summarize-and-drop for long convos.
  - Principle: optimize the encoding (resolution/format), not the content — you can't know what's "unnecessary" before the model reads it.

## Known limits (documented, not bugs)
- Substring grading has a variance floor — same code can flip pass/fail on identical case due to LLM non-determinism (observed on refund case)
- Threshold + stopwords tuned by eyeball, never measured — reranking backlog item addresses this
- Router is binary at retrieval level; an ID-bearing query that also needs KB ("order NW-10001 late, what's your refund policy?") may skip retrieval. Rare, accepted for v1.
- Attachments sent whole, one file per ticket assumed. Multi-file retrieval + per-turn resend avoidance not built — fine at current scale.