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
- Prompt caching — cache_control ephemeral (5-min) on stable system block; system refactored to block list (stable prefix first, variable context/retry after breakpoint). Verified empirically: inert below ~1024-token threshold, fires once realistic (created=1038 / read=1038). Cost model: 1.25x write (5m) / 2x (1h) / 0.1x reads. Cost lever first, latency second, input-side only.
- Customer ID normalization — normalize_id extracts digits + zero-pads via zfill ("cust-1" → CUST-001). Customer IDs only (order IDs typed exactly — normalizing them would be wrong). Nested-format-spec bug caught by Claude Code review, fixed.
- MCP — complete, all three primitives:
  - Tools: order status + customer orders wrapped as FastMCP server (schema auto-generated from type hints + docstrings). Agent is the MCP client — core chain refactored async top-down (run_agent → generate_answer → tool_loop), session threaded through, tool calls over stdio (call_tool → unwrap result.content[0].text). 6/6 evals through the MCP path.
  - Resources: KB article via kb:// URI. Exposed for cross-agent consumption; agent itself uses RAG for retrieval.
  - Prompts: 2 server-side templates, one parameterized (order_id auto-schema'd from function signature). Client exercises all primitives (list_/call_/read_/get_).
- Streamlit demo UI (src/ui.py) — delegated to Claude Code (first Claude Code task — JD gap closed): chat w/ history, file upload → multimodal path, signal badges (route/verify/cache/tools/fallback), sidebar convo switcher on conversations.py. agent.py signals dict added (guarded, evals untouched). Run: `streamlit run src/ui.py`. Caveat: badges session-only.
  - v2 (perf + polish): MCPBridge — one persistent MCP subprocess + session on a background event loop, cached via @st.cache_resource, auto-restart on dead subprocess. Killed the ~1-2s spawn-per-message (was fresh session per turn). Styled badge pills (colored) replacing plain captions, tinted bubbles, immediate user-echo + spinner, verify-fail reasons in an expander. sys.path shim so `streamlit run src/ui.py` resolves `src.*` imports. Remaining per-turn latency is the agent's 3 sequential LLM calls, not the UI.
- Docs/README (Phase 5) — README written from full-project survey: features, 3 interfaces (UI/CLI/evals) w/ commands, quickstart (.env keys: ANTHROPIC_API_KEY + VOYAGE_API_KEY), chain diagram, project structure, tech stack. assets/atlas_pipeline.svg authored (request pipeline: entry → classify/RAG/generate/verify + retry loop → MCP server → data; white-card bg for GitHub light/dark, render-checked). Existing atlas_architectures.svg moved into assets/. requirements.txt: added 3 undeclared runtime deps (rank-bm25, numpy, voyageai).
- LangGraph port (src/langgraph_agent.py) — full chain re-implemented as a graph, FULL LangChain transport (deliberate: "if transporting, transport fully"):
  - AgentState TypedDict (query/messages/route/context/answer/grounding/passed/reason/attempt) — loop state became graph state (attempt counter explicit).
  - Nodes: classify, retrieve, generate (LangChain tool loop: bind_tools → response.tool_calls → ToolMessage(tool_call_id) round-trip), verify, fallback. Nodes return deltas only; nodes never call nodes — the graph wires them.
  - Edges: entry classify → retrieve → generate → verify; conditional after_verify → END | generate (retry as BACKWARD EDGE — cycles are the loops) | fallback (attempt ≥ 2 guard). Retry reason injected into system prompt on regenerate.
  - Provider swap demonstrated: ChatOpenAI → OpenRouter (base_url + OPENROUTER_API_KEY) → gpt-4o. Same .invoke() regardless of backend.
  - Message choreography: System → Human → AI(tool_calls) → Tool → ... → AI(final). LangChain response.content IS the string (vs Anthropic content[0].text); invoke takes a LIST; no stop_reason — check response.tool_calls.
  - KB and tool paths both verified end to end through the compiled graph. Same agent now exists twice: hand-rolled (raw SDK) + framework (LangGraph) — the comparison artifact.
- Hand-rolled-vs-LangGraph comparison (interview artifact) — written short take on when a framework earns its keep. Thesis from the port: (1) separation — hand-rolled tangled everything in one method, the graph forces node boundaries; (2) modularity — reusable nodes, rewired edges, multiple graphs from shared parts; (3) isolation — retry lives in one edge function, changeable without touching generate/verify. Honest limit: the tool loop stayed imperative inside a node, and a 5-node linear chain barely exercises the graph — framework earns its keep when composing/modifying many graphs, overhead for one fixed chain.
- Langfuse (observability — JD keyword gap CLOSED) — CallbackHandler on the compiled graph (config callbacks), both KB and tool paths traced live in cloud dashboard. Nested spans per node, per-call generations with tokens/cost. user_id + session_id tags (Users tab grouping). `grounded` score written from verify (1/0) → pass-rate over time. Verified: traces, cost, user/session, score=1.00 all visible.

## Now
- Phase 5 polish: README + pipeline SVG DONE. Left: demo script, 90s walkthrough. Then applications start.

## Next
- Cleanup pass — dead code (classify regex, send_to_claude, tool_loop/extract_reply imports in langgraph_agent), duplicated extract_reply, debug prints, split chat.py, activate_chat broken since async refactor
- Reranking + top-k tuning — measured vs eyeballed; tune against eval suite (k=3/5/8)
- Multi-agent contrast exercise — orchestrator + specialists as LangGraph subgraphs, measured vs chain; document why chain wins
- Optional cloud deploy (closes K8s + cloud JD gaps)

## Backlog
- Vector DB / RAG scaling (JD "Vector Databases" — required) — O(n) cosine loop breaks past a few thousand chunks. Swap for vector DB + ANN (FAISS/pgvector/Pinecone), keep BM25 + RRF, add rerank. Near end.
- Expand eval coverage — multi-turn, tool disambiguation, retrieval failure, non-determinism (run N, average); also point evals at the LangGraph app for apples-to-apples scoring
- Attachment token optimization — downscale images, text-PDF→text, send-once + cache. Optimize encoding not content.
- Data generator realism — partially fixed
- [VOCABULARY — interview prep, not a build] Agent memory taxonomy mapped to Atlas: working/in-context (have), retrieval (have), semantic/persistent (partial), parametric (n/a), episodic (verify logging), procedural (the chain; MCP prompts = managed version), prospective (niche). Collapses to 3 buckets: in-context, retrieval, persistent state.

## Known limits (documented, not bugs)
- Substring grading variance floor (LLM non-determinism)
- Threshold + stopwords + top-k eyeballed (reranking pass addresses)
- Router binary at retrieval level (rare miss, accepted v1)
- Attachments sent whole, one file/ticket
- LangGraph port: fresh messages built per generate (multi-turn history not threaded into graph runs yet); evals not yet pointed at the graph version


## Target-role gap check (JD: "Gen AI Engineer - AZ", Jul 2026)
HAVE: Python (via build) · GenAI/LLMs (Anthropic + OpenAI via OpenRouter) · RAG/semantic search · Agentic AI + orchestration (hand-rolled chain AND LangGraph) · MCP (done, JD-named) · Orchestration frameworks (LangGraph — done + writeup) · Observability (Langfuse — done, JD-named) · API/microservices · SDLC/CI-CD · Docker · FinTech · Claude Code (first task done — UI delegation)
GAP: Kubernetes/Cloud (optional deploy)
Screening signal: "technically strong profiles only" + live screen → validates build-not-tutorial thesis.

## [CONCEPTUAL LITERACY — read, don't build]
Inference-layer awareness (vLLM, CUDA, quantization) — infra lane, NOT FDE. Vocabulary only: serving engines, KV cache/paged attention, quantization tradeoffs, TTFT/TPOT/tail latency. Guardrail: writing CUDA = off-path.

## [AUDIT]
Audit DLAI Agentic-AI Module 5 (planning/multi-agent comms, free) before building multi-agent contrast — vocabulary + design patterns, ~1hr, no cert needed