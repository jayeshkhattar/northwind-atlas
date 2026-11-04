# Engineering standards

These are the rules for changing Atlas. They are short on purpose. Each one exists because
the problem it prevents is cheap to cause and expensive to find later.

## Adding a tool

1. **Schema first.** Write the Anthropic tool schema in [src/tools.py](src/tools.py) before
   the function. The description should say when to use the tool *and when not to* (see
   `get_customer_orders`). The model chooses tools from these descriptions.
2. **Function with typed arguments.** FastMCP builds its input validation from the type
   hints, so `order_id: str` is what rejects `{"order_id": 123}` at the protocol boundary.
   Expected misses ("no such order") are return values, not exceptions. The model can
   recover from a result, but an exception just ends up as an error string.
3. **Register it in both places**: `mcp.tool()` in [src/mcp_server.py](src/mcp_server.py),
   and `TOOL_FUNCTIONS` plus the `TOOLS` list in [src/agent.py](src/agent.py).
   `test_server_exposes_the_tools_the_model_is_told_about` fails if the two drift apart.
4. **Tests** in [tests/test_mcp_tools.py](tests/test_mcp_tools.py): one valid input, the
   malformed inputs (missing field, wrong field, wrong type), and the output checked against
   a JSON schema. Add the tool to `VALID` and the parametrized tests pick it up.
5. **Tracing comes free.** `tool_loop` wraps every MCP call in a `tool.<name>` span with
   the input, output size, error flag and latency. If the tool has a cost or quota, add it
   as a `tool.*` attribute.
6. **At least one eval case** that needs the tool to answer.

## Adding an eval case

Add an object to [evals/cases.json](evals/cases.json) with a unique `id`, a `category`,
the `input`, and a grader:

- `"grader": "code"` with `expected` as a list of strings that must all appear in the reply.
  Use this whenever the right answer contains a checkable fact (an order status, a number
  of days). It's deterministic and free.
- `"grader": "model"` with `expected` as one sentence describing a passing answer. Use this
  only for behavior a substring can't check, mostly *not* doing something (inventing a
  phone number, confirming a false premise).

Then run `python -m src.evals --mode live --only <id>` until the case does what you want.
Run `make evals-record`, and commit `evals/cases.json`, `evals/cassette.json` and
`evals/badge.json` together. A case that fails is fine to commit if it documents a known
gap. Say so in the PR, and the pass rate keeps you honest about it.

## Before merge

CI runs all of this. Run it locally first:

| Check | Command | Must be |
|---|---|---|
| Lint | `make lint` | clean |
| Unit tests | `make test` | all pass, offline, under 30 s |
| Evals (replay) | `make evals` | pass rate ≥ threshold, zero cassette misses |

If the change touches anything that reaches the model (prompts, retrieval, chunking, tool
output, message assembly), replay will fail with a cassette miss. That is intended. Run
`make evals-record` against the real API, and put the before and after pass rates in the PR
description. Reviewers read the cassette diff the way they read a snapshot test diff.

## Prompts

Prompts are code. They live in [src/agent.py](src/agent.py) (`SYSTEM_PROMPT`, the
classifier prompt in `classify_llm`, the verifier prompt in `verify`) and the grader prompt
in [src/evals.py](src/evals.py), and they're versioned by git like everything else. There is
no separate prompt registry, because the cassette already does that job: its keys hash the
full request (model, system blocks, messages, tools, max_tokens), so a prompt edit cannot
merge without a re-record and a fresh pass rate. Each eval report records `git_sha` and
`agent_model`, so any score can be traced back to the exact prompts that produced it.

Changing the model counts as a prompt change: same process, re-record and compare.

## Reproducing a bug from a production trace

1. **Find the turn.** Filter traces on `atlas.escalated = true`,
   `verify.verdict = FAIL`, or `tool.is_error = true`. The `atlas.turn` span has the query
   and the final answer.
2. **Locate the failing layer** from the child spans, without re-running anything:
   - `retrieval`: did `retrieval.fused` contain the chunk that answers the question? If not,
     it's a retrieval bug. Compare `retrieval.bm25` with `embedding.top_scores` to see which
     index missed.
   - `tool.*`: was `tool.input` right? Was the output what the data says?
   - `llm.generate`: did the answer drop or invent something that was in the context?
   - `verify.gate`: is the `verify.reason` correct, or is the verifier wrong?
3. **Turn it into an eval case**, using the trace's query as `input` and the correct answer
   as `expected`. Run it with `--only` in live mode and confirm it fails the same way.
4. **If the bug is in deterministic code** (retrieval, a tool, message assembly), write a
   unit test too. Unit tests run on every commit for free; evals cost API calls.
5. Fix it, re-record, and the case stays in the suite as a regression guard.

For local debugging, `python -m scripts.trace_dump "<query>"` prints the same span tree for
one turn without a tracing backend.
