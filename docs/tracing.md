# Tracing

Every agent turn produces one OpenTelemetry trace. The code is in
[src/tracing.py](../src/tracing.py), and the spans are opened in `agent.py`, `search.py` and
`embeddings.py`.

## Turning it on

Tracing is off unless `ATLAS_TRACING` is set. When it's off, the OpenTelemetry API returns a
no-op tracer, so the quickstart and the test suite need no extra credentials.

| `ATLAS_TRACING` | Where spans go | Needs |
|---|---|---|
| unset / `off` | nowhere (no-op) | — |
| `console` | JSON on stderr | — |
| `otlp` | any OTLP/HTTP collector (Jaeger, Tempo, Honeycomb, ...) | `OTEL_EXPORTER_OTLP_ENDPOINT` |
| `langfuse` | Langfuse, through its OTLP endpoint | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` |

Langfuse is used as an OTLP backend rather than through its own SDK, so switching vendors is a
config change and the instrumentation stays the same. Each span carries
`langfuse.observation.type` (`agent`, `generation`, `retriever`, `tool`, `guardrail`,
`embedding`), which Langfuse uses to render generations and tools properly. Other backends
just show it as an attribute.

To see a single turn without any backend:

```bash
python -m scripts.trace_dump "What's the status of order NW-10001?"
```

## What is traced

```
atlas.turn                      [agent]      one per user message
├── llm.classify                [generation] router call
├── retrieval                   [retriever]  skipped when route = TOOL
│   └── embedding.query         [embedding]  Voyage query embedding + cosine search
├── llm.generate                [generation] one per model call in the tool loop
├── tool.<name>                 [tool]       one per MCP call
├── llm.generate                [generation] the call after the tool result
└── verify.gate                 [guardrail]  one per attempt
    └── llm.verify              [generation]
```

| Span | Attributes | Why it's there |
|---|---|---|
| `atlas.turn` | query, route, history length, attachment, `verify.attempts`, `atlas.escalated`, final answer, `langfuse.session.id` | The unit you search by. "Show me every escalated turn yesterday" is a filter on one attribute. |
| `llm.*` | request model, max_tokens, response model, stop reason, input/output tokens, cache write/read tokens, latency | Cost and latency per call site. It also shows whether prompt caching is actually hitting (`cache_read_input_tokens > 0` after the first turn). |
| `retrieval` | query, top_k, BM25 threshold, top-5 BM25 scores, how many BM25 hits cleared the threshold, semantic hits, fused ranks with RRF scores | When an answer is wrong, the first question is whether the right chunk was retrieved. These attributes answer it without re-running anything. |
| `embedding.query` | model, top-5 cosine similarities | Separates "the embedding missed" from "BM25 missed". |
| `tool.<name>` | tool name, input as sent, tool_use id, output size in bytes, `tool.is_error`, latency; exceptions are recorded on the span | MCP calls cross a process boundary. This is where timeouts and malformed inputs show up. |
| `verify.gate` | attempt number, max attempts, verdict, failure reason | The gate is the main safety mechanism. Its pass rate and reasons are the first thing to look at after a prompt change. |

The customer's text and the agent's answer are recorded because this is a demo with
synthetic data. Free text appears in `atlas.query`, `atlas.answer`, `retrieval.query`,
`verify.reason` and `tool.input`. With real customer data, drop or hash those five
attributes. Everything else is counts, scores, IDs and timings.

## A real trace

<!-- TRACE_DUMP -->
