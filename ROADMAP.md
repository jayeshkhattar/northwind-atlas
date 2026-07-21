# Atlas — Production Upgrade Roadmap

**Goal:** Evolve Atlas from a course capstone into a production-grade agentic support system that closes every Tier-1/2 JD gap (observability, MCP, eval frameworks, CI/CD, Kubernetes) — one repo, one demo, every resume bullet defensible in a deep dive.

**Target roles:** AI Forward Deployed Engineer / Lead AI Engineer (Bain AIS-class), $200k+, ~4–5 month window.

**Operating rules**
- Build for real, minimally. No claim goes on the resume until it runs.
- Every milestone ends in a runnable, committed state. Commit working checkpoints every ~2 hours on long build days.
- One project. All upgrades land on Atlas — no scattered repos.

---

## Current State (baseline, pre-roadmap)

- [x] RAG pipeline — BM25 + Voyage AI semantic embeddings + RRF fusion
- [x] Tool use — Northwind support tools (order lookup, product search, etc.)
- [x] Persistent conversation management
- [x] Custom prompt evals harness
- [x] Hallucination fix
- [x] LLM-based query routing
- [x] Multimodal intake
- [x] Orchestration chain with retry logic
- [x] Prompt caching

**Known gaps vs. target JDs:** MCP (top priority), observability, eval-framework fluency (Ragas/DeepEval), CI/CD story, Kubernetes/cloud deploy, Claude Code hands-on use.

---

## Phase 1 — Observability: Langfuse (≈ 8 hrs)

**Why:** #1 flagged gap; every 2026 agentic-role loop asks "what do you trace, what's on your dashboard."

### Tasks
- [ ] `pip install langfuse`; create Langfuse Cloud project (free tier, 50k obs/mo); store keys in `.env`
- [ ] Instrument the chain with SDK **v3** decorators (`@observe`, `get_client()` — ignore v2 `langfuse.trace()` tutorials):
  - [ ] `@observe()` on router, retrieval (BM25 + Voyage + RRF), orchestration steps
  - [ ] `@observe(as_type="generation")` on all Claude calls
- [ ] Verify in UI: one trace per user query with nested spans (route → retrieve → generate → tool calls), latency per span
- [ ] Add interview-grade metadata:
  - [ ] Model name + token counts on generation spans (auto cost attribution)
  - [ ] `user_id` / `session_id` so multi-turn conversations group into sessions
  - [ ] Tag traces with route decision (`route:billing`, `route:technical`) → cost-per-route filtering
- [ ] Trace one retry path: failed tool call + retry as child span with `level="ERROR"`
- [ ] Push existing eval-harness results as trace scores (`trace.score(name="hallucination", value=...)`)

### Deliverable
Screenshot-able dashboard: traces, per-span latency, cost per query, cost by route, eval scores. One traced production-style failure.

### Resume bullet (after completion)
> Instrumented multi-step agentic workflows with Langfuse — span-level tracing, token/cost attribution per route, and eval scores integrated into production traces.

---

## Phase 2 — MCP: Server + Client (≈ 8 hrs)

**Why:** The 2026 filter question. Server-only is table stakes; Atlas-as-MCP-client is the differentiator.

### Part A — Server (≈ 4 hrs)
- [ ] `pip install "mcp[cli]"`; scaffold with FastMCP (`northwind-support` server)
- [ ] Extract Atlas's Northwind tools into `@mcp.tool()` functions
- [ ] Run over stdio; connect to Claude Desktop via config; verify Claude Desktop drives Atlas tools

### Part B — Hardening + Client (≈ 4 hrs)
- [ ] Add 2–3 more tools
- [ ] Add one **resource** (e.g. `northwind://products` catalog)
- [ ] Add one **prompt template** → all three MCP primitives covered
- [ ] Refactor Atlas into an **MCP client**: replace hardcoded tool dispatch with MCP client calls to own server
- [ ] Update architecture diagram: `agent → MCP → tools`

### Deliverable
Working MCP server consumable by Claude Desktop; Atlas consuming its own tools over MCP.

### Resume bullet
> Built MCP servers exposing agent tools, resources, and prompt templates; refactored agent tool dispatch to an MCP client architecture.

---

## Phase 3 — Eval Frameworks: Ragas / DeepEval (≈ 4 hrs)

**Why:** Converts "I built a custom harness" into framework fluency + a comparison story interviewers love.

### Tasks
- [ ] Port 5–10 cases from the custom harness to Ragas (faithfulness, answer relevancy, context precision on RAG outputs)
- [ ] Push Ragas scores into Langfuse via `trace.score()` — lands on the Phase 1 dashboard
- [ ] Write down (while fresh, in `docs/evals-comparison.md`):
  - [ ] 2 things the custom harness catches that Ragas doesn't
  - [ ] 2 things Ragas catches that the custom harness doesn't

### Deliverable
Ragas suite runnable via one command; scores visible in Langfuse; written comparison doc.

### Interview line
> "I built custom evals first, then adopted Ragas — here's what each catches that the other misses."

### Resume bullet
> Designed evaluation frameworks combining a custom assertion harness with Ragas metrics (faithfulness, relevancy, context precision), integrated into observability traces.

---

## Phase 4 — CI/CD: GitHub Actions (≈ 1 week, part-time)

**Why:** Completes the deploy story already 70% built (Docker Compose + Caddy + FastAPI on DigitalOcean for the trading system — same pattern applies).

### Tasks
- [ ] Add pytest coverage for deterministic components (routing logic, retrieval fusion, chunking)
- [ ] Pipeline stage 1 — on push: lint (ruff) + tests
- [ ] Pipeline stage 2 — on main: build Docker image, push to registry
- [ ] Pipeline stage 3 — deploy: SSH/action deploy to droplet (or k3s in Phase 5), health-check gate
- [ ] Smoke-test eval subset as a CI gate (fail build on regression) — ties Phase 3 into CI ("regression evaluation" per JD language)

### Deliverable
Green pipeline badge; push-to-deploy with eval regression gate.

### Resume bullet
> Built CI/CD pipelines (GitHub Actions) with automated tests and eval-regression gates for agentic services; containerized deploys to cloud infrastructure.

---

## Phase 5 — Kubernetes: k3s (≈ 1 week, part-time)

**Why:** Honest, defensible K8s claim without pretending to run EKS at scale.

### Tasks
- [ ] Install k3s locally (M5 Mac) or on a throwaway ~$20 droplet
- [ ] Write manifests: Deployment + Service + Ingress for Atlas API
- [ ] Add liveness/readiness probes
- [ ] Add HPA (CPU-based is fine)
- [ ] ConfigMap/Secret for env + API keys
- [ ] Point Phase 4 pipeline at k3s (kubectl apply step)
- [ ] Tear down / document teardown

**Prep check:** be able to explain every line of the manifests — the claim must survive "walk me through your Deployment spec."

### Deliverable
Atlas running on k3s with probes + HPA; manifests in repo under `deploy/k8s/`.

### Resume bullet
> Containerized and deployed agentic services to Kubernetes (k3s) with health probes, autoscaling, and manifest-driven CI/CD.

---

## Phase 6 (Deferred) — Fine-tuning: LoRA/QLoRA via MLX

**Only if a target role demands PEFT.** Doesn't attach to Atlas naturally.

- [ ] One MLX fine-tune of a small model (Llama/Qwen) on M5 Mac — candidate dataset: Pine Script → Python translation pairs
- [ ] Eval before/after on a held-out set
- [ ] Defensible claim: dataset size, base model, method, eval delta

**Explicitly skipped:** PySpark/Databricks — different job family, dilutes positioning.

---

## Schedule

| When | What |
|---|---|
| Weekend 1 (2 × 8 hr days) | Phase 1 (Sat AM) → Phase 2A (Sat PM) → Phase 2B (Sun AM) → Phase 3 (Sun PM). Stretch: pull Phase 4 lint+test stage forward (~2 hrs). |
| Week 2 | Phase 4 |
| Week 3 | Phase 5 |
| Buffer / as needed | Phase 6, interview prep with the demo |

**Ahead-of-plan target:** Tier 1 + 2 closed in ~3 weeks vs. original 6-week estimate.

---

## End State — the demo script

One repo, one dashboard, one walkthrough:

1. User query → Claude Desktop or Atlas UI
2. Trace appears in Langfuse: route → MCP tool calls → RAG retrieval → generation, with latency + cost per span
3. Show cost-by-route filtering
4. Show a traced failure + retry
5. Show Ragas + custom eval scores on the same trace
6. Show the CI pipeline: push → tests → eval gate → build → deploy to k3s
7. `kubectl get pods` — Atlas running with probes + HPA

**Elevator claim:** "Production-grade agentic support system — hybrid RAG, LLM routing, MCP architecture, span-level observability with cost attribution, framework-based evals gated in CI, deployed on Kubernetes."

Every phrase in that sentence maps to a phase above and survives a whiteboard.

---

## Progress Log

| Date | Phase | Notes |
|---|---|---|
| _(fill as you go)_ | | |