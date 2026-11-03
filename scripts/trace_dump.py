"""Run one agent turn and print its trace as an indented tree.

    python -m scripts.trace_dump "how long do refunds take?"

Uses an in-memory exporter, so it works without a Langfuse account. Makes real
Anthropic + Voyage calls.
"""
import asyncio
import json
import sys

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.tracing import init_tracing

exporter = InMemorySpanExporter()
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter))
init_tracing(provider)

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

from src.agent import extract_reply, run_agent  # noqa: E402

SKIP = {"langfuse.observation.type"}


def fmt(value, width=110):
    text = value if isinstance(value, str) else json.dumps(value)
    return text if len(text) <= width else text[: width - 3] + "..."


def print_tree(spans):
    children = {}
    for s in spans:
        parent = s.parent.span_id if s.parent else None
        children.setdefault(parent, []).append(s)

    def walk(parent, depth):
        for s in sorted(children.get(parent, []), key=lambda x: x.start_time):
            attrs = dict(s.attributes)
            latency = attrs.pop("latency_ms", None)
            kind = attrs.get("langfuse.observation.type", "span")
            print(f"{'  ' * depth}{s.name}  [{kind}]  {latency} ms")
            for key, value in attrs.items():
                if key not in SKIP:
                    print(f"{'  ' * depth}    {key} = {fmt(value)}")
            walk(s.context.span_id, depth + 1)

    walk(None, 0)


async def main(query):
    params = StdioServerParameters(command=sys.executable, args=["-m", "src.mcp_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            messages = await run_agent(session, [], query, conversation_id="trace-demo")
    print(f"reply: {extract_reply(messages)}\n")
    print_tree(exporter.get_finished_spans())


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "how long do refunds take?"))
