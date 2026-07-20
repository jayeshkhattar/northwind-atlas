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
- Prompt caching — cache_control ephemeral (5-min TTL) on stable system block; system refactored to block list (stable prefix first, variable context/retry after breakpoint). Verified empirically: inert below ~1024-token threshold (created=0/read=0), fires once prompt realistic (created=1038 write, read=1038 on repeat, ~10% cost). Hardened system prompt in process. Cost model: 1.25x write (5m) / 2x (1h) / 0.1x reads; break-even 1 read (5m) / 2 reads (1h). Read cost identical both TTLs — only write differs. Primarily a cost lever, secondarily latency, input-side only (output untouched).
- MCP integration — tools wrapped as FastMCP server (schema auto-generated from type hints + docstrings); agent is the MCP client. Refactored core chain async top-down (run_agent → generate_answer → tool_loop), session threaded through, tool calls go over stdio to the server subprocess (call_tool → unwrap result.content[0].text). Both tools (order status, customer orders) live over protocol. 7/7 evals through the MCP path — behavior identical to direct calls, proven by suite.

## Now

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

## Target-role gap check (from real JD: "Gen AI Engineer - AZ", Jul 2026)
Representative of roles J wants. Atlas maps to it strongly.

HAVE (Atlas covers):
- Python (in progress via this build) · GenAI/LLMs (Anthropic) · RAG/vector/semantic search (done) · Agentic AI + orchestration (chain done) · API/microservices (Salesforce/MuleSoft bg) · SDLC/CI-CD (Copado) · Docker (VPS work) · FinTech domain (bank via Infosys)

GAP — drives prioritization:
- MCP/CLI — named explicitly in JD. → MCP is the priority build after current Features win.
- Observability for AI workflows — JD "preferred". → Langfuse graduates from backlog; do after next measured improvement (double duty: real tracing + JD keyword).
- Kubernetes — not touched. Minor; optional cloud deploy would close it.
- Cloud (Azure/AWS/GCP) — not touched. One containerized cloud deploy of Atlas closes this + K8s together.
- Claude Code — flagged as separate skill; do one small task in it before applying.

Screening signal: JD demands "technically strong profiles only" + mandatory live technical screen. Validates the whole thesis — they screen for depth/live-debugging, which is exactly what building (not tutorial-ing) Atlas prepares for.

- [CONCEPTUAL LITERACY — read, don't build] Inference-layer awareness. NOT an FDE build task and NOT on target JDs — this is the model-serving/infra lane (vLLM, CUDA, quantization). Value for an FDE is *vocabulary only*: being able to reason about and speak to latency/cost/model behavior without building the runtime. Skim-level familiarity, no implementation:source .venv/bin/activate
  - Serving & engines: vLLM, TensorRT-LLM, TGI, llama.cpp, Ollama — what they are, when each is used.
  - KV cache + paged attention — why long context is expensive; connects to prompt caching (which IS my lane).
  - Quantization (FP16/BF16/INT8/INT4, GPTQ/AWQ/GGUF) — the accuracy/cost tradeoff, one sentence each.
  - Perf metrics: TTFT, TPOT, throughput, tail latency — the vocabulary for talking about latency.
  - Production serving: autoscaling, load balancing, observability (Prometheus/Grafana) — overlaps with the Langfuse observability work, which IS on my path.
  Guardrail: if I catch myself writing CUDA or building an inference engine, I've drifted off the FDE path. This box is closed by *reading a few explainers*, not code.