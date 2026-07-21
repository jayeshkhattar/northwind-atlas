# Atlas — Build Progress
Project: Northwind support/ops agent. Learning mode (I write code, Claude reviews).

## Done
- Phase 0: env, repo, data generation (customers.json, orders.json)
- Phase 1: full RAG pipeline — chunking, BM25, embeddings (Voyage, cached), multi-index RRF fusion, stopwords, BM25 threshold guard
- Phase 1: agent loop + multiple tools (get_order_status, get_customer_orders) with dict dispatch
- Phase 1: unified agent — RAG context + tools in one call
- Conversation management: multi-turn memory + persistent JSON storage (load/save/display, auto-increment ids), survives restarts
- Evals: full harness — dataset (input/expected/grader shape), runner with per-case dispatch, code grader (case-insensitive substring, robust to en-dash traps), model grader (constrained one-word output, `startswith("PASS")` defensive parse). 6/6.
- Hallucination fix — fabricated support email + phone in escalation path. Root cause: "don't invent policies" too narrow (a phone number isn't a policy). Fix: generalized no-fabrication rule w/ explicit categories (contact details, policies, prices). Eval-driven: red → change → green.
- Query routing — v1 regex (NW-/CUST-) → v2 LLM classifier (KB/TOOL/BOTH). Removes ID-pattern brittleness; classifies by intent, scales to new tables without new regex. Tools always-on regardless of route (graceful misroute). 6/6.
- Multimodal intake — image + PDF via load_file_block (base64; image→"image", PDF→"document", ext-driven media_type, raises on unsupported). Optional file_path param, text callers unaffected. Verified live (PNG + PDF).
- Orchestration chain (verify node) — classify → generate_answer (tool loop, extracted fn) → verify (grounding gate: judges answer vs real KB context + tool results, returns verdict+reason) → retry-with-reason (max 2, reason injected) → safe fallback. Untangled nested tool/retry loops via extraction. 6/6; caught real UnboundLocalError during refactor.
- Prompt caching — cache_control ephemeral (5-min) on stable system block; system refactored to block list (stable prefix first, variable context/retry after breakpoint). Verified empirically: inert below ~1024-token threshold (created=0/read=0), fires once realistic (created=1038 / read=1038 on repeat). Hardened system prompt in process. Cost model: 1.25x write (5m) / 2x (1h) / 0.1x reads; break-even 1 read (5m) / 2 (1h). Cost lever first, latency second, input-side only.
- Customer ID normalization — normalize_id extracts digits + zero-pads ("cust-1" → CUST-001) so users needn't type exact IDs. Applied to customer IDs only (order IDs are full 5-digit, typed exactly — normalizing them would be wrong).
- MCP — complete, all three primitives:
  - Tools: order status + customer orders wrapped as FastMCP server (schema auto-generated from type hints + docstrings). Agent is the MCP client — core chain refactored async top-down (run_agent → generate_answer → tool_loop), session threaded through, tool calls go over stdio to server subprocess (call_tool → unwrap result.content[0].text). 6/6 evals through the MCP path — behavior identical to direct calls.
  - Resources: KB article via kb:// URI. Exposed for cross-agent consumption / protocol completeness; agent itself uses RAG for retrieval, not resources.
  - Prompts: 2 server-side templates, one parameterized (order_id auto-schema'd from function signature). Client discovers + invokes all three primitives (list_/call_/read_/get_).

## Now
- LangGraph port — re-implement the orchestration chain in LangGraph as a hand-rolled-vs-framework comparison. JD "AI orchestration frameworks" keyword. Deliverable: working port + short written take on when a framework earns its keep. Differentiator: built the machinery by hand first, so the port proves fundamentals AND framework fluency.

## Next
- Cleanup pass — dead code (classify regex, send_to_claude), duplicated extract_reply (agent.py + evals.py), debug prints ([route:]/[verify:]/[cache:]), split chat.py out of agent.py, activate_chat needs async+session update (broken since MCP refactor)
- Langfuse — trace/observe runs, pass-rate over time (also JD "observability" keyword)
- Reranking + top-k tuning — measured alternative to eyeballed threshold; tune both against eval suite (k=3/5/8)
- Multi-agent contrast exercise — orchestrator + specialists, measured vs chain; document why chain wins
- Optional cloud deploy (closes K8s + cloud JD gaps)
- Phase 5: README, demo script, 90s walkthrough

## Backlog
- Vector DB / RAG scaling (JD "Vector Databases" — required) — current semantic search is hand-written O(n) cosine loop over vectors.json; breaks past a few thousand chunks. Fix: swap for vector DB + ANN (FAISS/pgvector/Pinecone), keep BM25 + RRF, add rerank. Do properly near end as dedicated scaling exercise; not needed for demo.
- Expand eval coverage — multi-turn memory, tool disambiguation, retrieval failure, non-determinism (run N, average)
- Attachment token optimization — downscale images (Pillow ~1000–1500px), text-PDF→text block (pdfplumber), send-once + cache prefix, summarize-and-drop. Principle: optimize encoding not content.
- Data generator realism — partially fixed
- [VOCABULARY — interview prep, not a build] Agent memory taxonomy mapped to Atlas: working/in-context (messages list — have), retrieval/external (RAG — have), semantic/persistent (conversations.py — partial), parametric (weights — nothing to build), episodic (past-run log — connects to verify logging), procedural (workflows — the chain IS this; MCP prompts = managed version), prospective (future intentions — niche, trading not support). Real engineering collapses to 3: in-context, retrieval, persistent state. Layer to the problem, don't build all 7.

## Known limits (documented, not bugs)
- Substring grading has a variance floor (LLM non-determinism flips pass/fail on identical case)
- Threshold + stopwords + top-k eyeballed, never measured (reranking pass addresses)
- Router binary at retrieval level; ID-bearing query that also needs KB may skip retrieval. Rare, accepted v1.
- Attachments sent whole, one file/ticket assumed. Multi-file retrieval + resend-avoidance not built.

## Target-role gap check (from real JD: "Gen AI Engineer - AZ", Jul 2026)
HAVE: Python (via build) · GenAI/LLMs (Anthropic) · RAG/semantic search · Agentic AI + orchestration (chain) · MCP (done, JD-named) · API/microservices (Salesforce/MuleSoft) · SDLC/CI-CD (Copado) · Docker · FinTech (bank via Infosys)
GAP: AI orchestration frameworks (LangGraph — building now) · Observability (Langfuse — next) · Kubernetes/Cloud (optional deploy closes both) · Claude Code (one small task before applying)
Screening signal: "technically strong profiles only" + mandatory live technical screen → validates the build-not-tutorial thesis.

## [CONCEPTUAL LITERACY — read, don't build]
Inference-layer awareness (vLLM, CUDA, quantization) — model-serving/infra lane, NOT FDE, NOT on target JDs. Value = vocabulary only (reason about latency/cost without building the runtime). Skim: serving engines (vLLM/TGI/llama.cpp/Ollama), KV cache + paged attention, quantization tradeoffs, perf metrics (TTFT/TPOT/throughput/tail latency). Guardrail: writing CUDA = drifted off-path. Closed by reading, not code.