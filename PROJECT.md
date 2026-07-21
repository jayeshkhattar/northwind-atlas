# Atlas — Project Charter & Curriculum Coverage

> Canonical reference for the Atlas build. Captures what the project is, why it
> exists, how we build it (the learning contract), and the full list of topics
> it must cover. Paste-in handoff for any fresh chat.

---

## 1. What this is

**Atlas** — a customer support & operations agent for a fictional D2C
coffee-gear brand, **"Northwind"** (grinders, espresso machines, beans,
accessories).

Atlas resolves customer tickets end to end: answers from a knowledge base,
takes real actions (order lookup, refunds, escalation), reads uploaded
screenshots and receipts, reasons about hard cases, and ships with an eval
harness that proves it works.

---

## 2. Why this project exists (the meta-goal)

- **Career goal:** transition to an **AI Forward Deployed Engineer (FDE)** role
  — US, **$200k+**, ~6-month horizon.
- This is the **flagship portfolio artifact** AND the vehicle for closing the
  real skill gap: **writing and debugging fresh Python under pressure** (the
  thing live coding interviews gate on).
- Built as the **capstone for the "Building with the Claude API" course** — one
  coherent system that exercises the whole curriculum in a real build, instead
  of disconnected tutorial exercises.

---

## 3. The build contract (learning-mode guidelines)

These are non-negotiable — they're the whole point of the project.

- **I write the code. Claude scopes, guides, and reviews** for correctness AND
  Python idioms (the Java/Apex → Python remap).
- Claude hands over **full code only for throwaway scaffolding** (boilerplate,
  folder setup, fixed catalogs) — **never for the parts that are the learning
  target** (agent logic, RAG, tool loops, evals).
- Claude may give **intentionally broken / incomplete code as fix-it &
  debugging exercises**, clearly labeled. Debugging is itself the FDE skill.
- Claude **holds the line** — does not just hand over finished logic even when
  it would be faster or when I ask for a shortcut.
- **Build locally** (my machine + repo + GitHub), **in chat** — not Claude
  Code / Cowork (those are agentic and would do the writing for me, defeating
  the purpose). Claude Code is a separate skill to pick up later on a throwaway
  task.
- **The repo is the memory.** `PROGRESS.md` holds state; work phase-by-phase so
  a context reset / fresh chat costs nothing. `requirements.txt` reproduces the
  environment on any machine.

---

## 4. Curriculum coverage — the full checklist

Everything below must be exercised by the build (or by a small labeled bolt-on
exercise). Grouped by course section.

### Foundations (used throughout, implicitly)
- [ ] Multi-turn conversations / message formatting
- [ ] System prompts
- [ ] Temperature
- [ ] Response streaming
- [ ] Structured data / structured output

### Prompt evaluation
- [x] Prompt evals (typical eval workflow)
- [x] Generating test datasets
- [x] Running the eval
- [x] Model-based grading
- [x] Code-based grading

### Prompt engineering
- [ ] Being clear and direct
- [ ] Being specific
- [ ] Structure with XML tags
- [ ] Providing examples

### Tool use
- [x] Using tools / tool functions
- [x] Tool schemas
- [x] Handling message blocks
- [x] Sending tool results
- [x] Multi-turn conversations with tools
- [x] Implementing multiple turns
- [x] Using multiple tools
- [ ] Fine-grained tool calling
- [ ] Text edit tool
- [ ] Web search tool

### RAG & agentic search
- [x] Text chunking (multiple chunking strategies)
- [x] Text embeddings
- [x] Implementing the full RAG flow
- [x] BM25 lexical search
- [x] Multi-index RAG pipeline

### Features of Claude
- [ ] Extended thinking (enabled and disabled)
- [ ] Redacted thinking + signature handling
- [ ] Image / vision support (image blocks, prompting around images)
- [ ] PDF support
- [ ] Citations
- [ ] Prompt caching (+ rules of prompt caching)
- [ ] Code execution and the Files API

### Model Context Protocol (MCP)
- [ ] MCP clients
- [ ] Project setup
- [ ] Defining tools with MCP
- [ ] Implementing a client
- [ ] Defining resources
- [ ] Accessing resources
- [ ] Defining prompts
- [ ] Prompts in the client
- [ ] MCP review

### Agents & workflows
- [ ] Parallelization workflows
- [ ] Chaining workflows
- [ ] Routing workflows
- [ ] Agents and tools
- [ ] Environment inspection
- [ ] Workflow vs agent (the distinction, made concrete)

---

## 5. Where each topic lives in the build (coverage map)

**Retrieval layer (the knowledge base)** → chunking (multiple strategies),
embeddings, full RAG flow, BM25, multi-index (semantic + lexical), citations on
every answer, prompt caching (cache system prompt + KB context), PDF support
(KB articles as PDFs).

**Tools / action layer** → order lookup, account lookup, refund, escalate
(schemas, multiple tools, multi-turn tool loops); web search when the KB misses;
text-edit tool drafts/revises the reply template.

**Multimodal intake** → customer uploads an error screenshot (image blocks +
prompting) and a receipt/invoice (PDF). 

**Code execution + Files API** → compute refund proration; process an uploaded
orders CSV.

**Reasoning layer** → extended thinking (enabled) for escalation decisions,
incl. redacted/signature handling; prompt engineering across the system prompt
and every tool description.

**Orchestration layer** → router classifies the ticket → chain resolves
multi-step → parallel search across indices. Agent-vs-workflow made concrete.

**MCP** → wrap the action tools as an MCP server; agent is the MCP client; KB
docs exposed as MCP resources; canned support prompts as MCP prompts. Covers
setup, defining tools/resources/prompts, accessing resources, prompts-in-client.

**Eval layer** → generated ticket test set; model-based + code-based grading
(right tool? right answer? escalated when it should?).

---

## 6. Build phases

- **Phase 0 — Setup (DONE):** venv, `anthropic` SDK, API key, repo skeleton,
  Northwind fake data (`customers.json`, `orders.json`).
- **Phase 1 — Core loop:** agent answers from KB + calls lookup tools.
  → RAG stack, tool use, citations, caching, prompt engineering.
- **Phase 2 — Intake + actions:** image + PDF intake; refund via code execution
  + Files API; web-search fallback; text-edit tool.
- **Phase 3 — Orchestration + MCP:** refactor into router/chain/parallel; wrap
  tools as MCP server, agent as client, add resources + prompts; extended
  thinking for escalation.
- **Phase 4 — Evals:** test dataset, model + code grading, fix what it surfaces.
- **Phase 5 — Polish:** README, demo script, 90-second interview walkthrough.

> **Build order note:** Evals are built early (not Phase 4) and used as the
> safety net for every later phase — the harness (dataset → runner → code +
> model grading) is already working, so each subsequent change is measured
> before it's kept. Phase numbers describe scope, not strict sequence.

Each phase: Claude scopes → I write the Python → Claude reviews for correctness
and idioms. ~2–3 focused sessions per phase.

---

## 7. The two honest asterisks

Two topics don't map perfectly onto a support agent and may become short,
labeled standalone exercises rather than forced into the main flow:

- **Text edit tool** — built for editing files/code. Least-forced hook: drafting
  and revising a support reply template / editing a ticket doc.
- **Code execution + Files API** — a support agent doesn't naturally run code.
  Honest hook: refund proration math, or processing an uploaded orders CSV.

Everything else is native to the build.

