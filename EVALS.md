# Evals

**Status: no real run recorded yet.** The pass rate, latency and regression demo below will
be filled in from the first `make evals-record` run. Until then CI skips the eval step, and
no numbers are shown here, because none have been measured.

## Cases

11 cases in [evals/cases.json](evals/cases.json), in four categories:

| Category | Cases | What it checks | Grader |
|---|---|---|---|
| `kb` | 3 | Answers from the knowledge base (refund timing, shipping to Canada, grinder warranty) | code |
| `tool` | 4 | Order and customer lookups over MCP, including a customer with two orders and a question about two orders at once | code |
| `both` | 1 | A question that needs the KB and a tool together | code |
| `no-fabrication` | 3 | Must not invent a phone number or a discount policy, and must not confirm a false premise | model |

## Graders

- **Code-based (8 cases).** The case passes if every string in `expected` appears in the
  reply, ignoring case. Deterministic and free.
- **Model-based (3 cases).** `claude-sonnet-4-5` gets the question, a one-sentence
  criterion and the reply, and answers PASS or FAIL. Used only for "didn't do X" behavior
  that a substring can't check.

The agent under test runs on `claude-haiku-4-5`.

## Running

```bash
make evals-live     # real API calls, prints the pass rate
make evals-record   # same, and saves every response to evals/cassette.json + the badge
make evals          # offline replay of the cassette (what CI runs)
```

Each run writes `evals/report.json` with pass rate by category and grader, latency
p50/p95/mean, escalations, verify retries, the git SHA and both model names.

## Results

Pending the first recorded run.

## A regression the harness catches

Planned: run `tool-customer-014` and `tool-customer-001` at commit `bd48eec`, before the
`normalize_id` fix. At that commit every `get_customer_orders` call crashed, so neither
reply can contain the customer's order IDs. The real output goes here once it has been run.
