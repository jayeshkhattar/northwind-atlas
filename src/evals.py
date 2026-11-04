"""Graded eval harness for the Atlas chain.

    python -m src.evals                                   # live: real API calls
    python -m src.evals --mode record                     # live, and save every model/embedding response to the cassette
    python -m src.evals --mode replay --threshold 0.8     # offline: serve responses from the cassette (CI)
    python -m src.evals --report evals/report.json --only tool-customer-001

Cases live in evals/cases.json. "code" cases pass when every expected string appears in
the reply; "model" cases are judged by a stronger model against a written criterion.

Replay is strict: a request that isn't in the cassette is an error, not a guess. That
means any change to prompts, retrieval, tool output or message assembly shows up in CI
as a cassette miss until someone re-records against the real API and reviews the diff.
"""
import argparse
import asyncio
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CASES_PATH = Path("evals/cases.json")
CASSETTE_PATH = Path("evals/cassette.json")
GRADER_MODEL = "claude-sonnet-4-5"


class CassetteMiss(Exception):
    pass


class Cassette:
    """Request-hash → recorded responses, for Anthropic messages and Voyage embeddings."""

    def __init__(self, path, mode):
        self.path, self.mode = Path(path), mode
        self.entries = json.loads(self.path.read_text()) if mode == "replay" else {}
        self.served = {}
        self.misses = []

    @staticmethod
    def key(kind, payload):
        blob = json.dumps(payload, sort_keys=True, default=str)
        return f"{kind}:{hashlib.sha256(blob.encode()).hexdigest()[:24]}"

    def through(self, kind, payload, call, dump, load):
        key = self.key(kind, payload)
        if self.mode == "replay":
            recorded = self.entries.get(key)
            index = self.served.get(key, 0)
            if not recorded:
                self.misses.append(key)
                raise CassetteMiss(f"{key} not in cassette; the request changed since recording (run make evals-record)")
            self.served[key] = index + 1
            return load(recorded[min(index, len(recorded) - 1)])
        response = call()
        if self.mode == "record":
            self.entries.setdefault(key, []).append(dump(response))
        return response

    def save(self):
        if self.mode == "record":
            self.path.write_text(json.dumps(self.entries, indent=1, sort_keys=True) + "\n")


def install_cassette(cassette):
    """Patch the SDK classes before src.* is imported (src.search embeds a query at import)."""
    import anthropic
    import voyageai
    from anthropic.resources.messages import Messages

    real_create = Messages.create
    real_embed = voyageai.Client.embed

    def create(self, **kwargs):
        return cassette.through(
            "messages", kwargs, lambda: real_create(self, **kwargs),
            dump=lambda m: m.model_dump(mode="json"),
            load=anthropic.types.Message.model_validate,
        )

    def embed(self, texts, model=None, **kwargs):
        return cassette.through(
            "embed", {"texts": list(texts), "model": model}, lambda: real_embed(self, texts, model=model, **kwargs),
            dump=lambda r: r.embeddings,
            load=lambda e: type("Embeddings", (), {"embeddings": e})(),
        )

    Messages.create = create
    voyageai.Client.embed = embed


def code_grade(output, expected):
    return all(e.lower() in output.lower() for e in expected)


def model_grade(client, query, output, expected):
    system = (
        "You are a helpful assistant that grades answers to customer support questions. "
        "You will be given a question, an expected answer, and an actual answer. "
        "Grade the actual answer based on whether it meets the expected answer's criteria. "
        "Reply in just PASS or FAIL."
    )
    msg = client.messages.create(
        model=GRADER_MODEL,
        max_tokens=10,
        system=system,
        messages=[{"role": "user", "content": f"Query: {query}\nExpected answer criteria: {expected}\nActual answer: {output}"}],
    )
    return msg.content[0].text.strip().upper().startswith("PASS")


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))]


async def run_cases(cases):
    import anthropic
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    from src.agent import extract_reply, run_agent

    grader = anthropic.Anthropic()
    params = StdioServerParameters(command=sys.executable, args=["-m", "src.mcp_server"])
    results = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for case in cases:
                signals = {}
                start = time.perf_counter()
                row = {k: case[k] for k in ("id", "category", "grader", "input", "expected")}
                try:
                    messages = await run_agent(session, [], case["input"], signals=signals, conversation_id=f"eval-{case['id']}")
                    row["latency_ms"] = round((time.perf_counter() - start) * 1000)
                    row["reply"] = extract_reply(messages)
                    if case["grader"] == "code":
                        row["passed"] = code_grade(row["reply"], case["expected"])
                    else:
                        row["passed"] = model_grade(grader, case["input"], row["reply"], case["expected"])
                except CassetteMiss as e:
                    row.update(passed=False, error=str(e), latency_ms=None, reply=None)
                row.update(
                    route=signals.get("route"),
                    verify_attempts=len(signals.get("verify", [])),
                    escalated=signals.get("fallback"),
                    tools=signals.get("tools"),
                )
                results.append(row)
                print(f"[{'PASS' if row['passed'] else 'FAIL'}] {case['id']}: {case['input']}", file=sys.stderr)
                print(f"    reply: {(row['reply'] or row.get('error', ''))[:200]!r}", file=sys.stderr)
    return results


def summarize(results, mode):
    def rate(rows):
        return {"cases": len(rows), "passed": sum(r["passed"] for r in rows),
                "pass_rate": round(sum(r["passed"] for r in rows) / len(rows), 3) if rows else None}

    latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        sha = None
    from src.agent import model_name
    return {
        **rate(results),
        "mode": mode,
        "agent_model": model_name,
        "grader_model": GRADER_MODEL,
        "git_sha": sha,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "latency_ms": {"p50": percentile(latencies, 50), "p95": percentile(latencies, 95),
                       "mean": round(statistics.mean(latencies)) if latencies else None},
        "escalations": sum(bool(r["escalated"]) for r in results),
        "retries": sum(max(0, r["verify_attempts"] - 1) for r in results),
        "errors": sum("error" in r for r in results),
        "by_category": {c: rate([r for r in results if r["category"] == c]) for c in sorted({r["category"] for r in results})},
        "by_grader": {g: rate([r for r in results if r["grader"] == g]) for g in sorted({r["grader"] for r in results})},
    }


def markdown(summary, results, threshold):
    lines = [f"### Atlas evals ({summary['mode']})", "",
             f"**{summary['passed']}/{summary['cases']} passed ({summary['pass_rate']:.0%})**"
             + (f", threshold {threshold:.0%}" if threshold is not None else ""), ""]
    if summary["mode"] != "replay":
        lines += [f"Latency p50 {summary['latency_ms']['p50']} ms, p95 {summary['latency_ms']['p95']} ms", ""]
    lines += ["| case | category | grader | result | route | verify attempts |", "|---|---|---|---|---|---|"]
    for r in results:
        result = "PASS" if r["passed"] else ("ERROR" if "error" in r else "FAIL")
        lines.append(f"| {r['id']} | {r['category']} | {r['grader']} | {result} | {r['route']} | {r['verify_attempts']} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=["live", "record", "replay"], default="live")
    parser.add_argument("--cassette", default=str(CASSETTE_PATH))
    parser.add_argument("--report", help="write the JSON report here")
    parser.add_argument("--threshold", type=float, help="exit 1 if pass rate is below this (0-1)")
    parser.add_argument("--only", nargs="+", help="case ids to run")
    args = parser.parse_args(argv)

    if args.mode == "replay":
        # No network in replay; the SDK clients only need a key to construct.
        os.environ.setdefault("ANTHROPIC_API_KEY", "replay")
        os.environ.setdefault("VOYAGE_API_KEY", "replay")
    cassette = Cassette(args.cassette, args.mode)
    if args.mode != "live":
        install_cassette(cassette)

    cases = json.loads(CASES_PATH.read_text())
    if args.only:
        cases = [c for c in cases if c["id"] in args.only]
    results = asyncio.run(run_cases(cases))
    cassette.save()

    summary = summarize(results, args.mode)
    report = {"summary": summary, "cases": results}
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, indent=2) + "\n")
    md = markdown(summary, results, args.threshold)
    print(md)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(md)

    if args.threshold is not None and summary["pass_rate"] < args.threshold:
        print(f"pass rate {summary['pass_rate']:.0%} is below threshold {args.threshold:.0%}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
