"""Offline test harness: no network, no API keys.

Voyage is replaced before any src module is imported (src.search embeds a query at
import time). Query vectors come from tests/fixtures/query_vectors.json, recorded once
from the real API; unknown text gets a deterministic pseudo-random vector.

Anthropic is replaced per test with FakeAnthropic, which answers by call site:
classify (max_tokens=10), generate (has tools), verify (max_tokens=100).
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)  # src modules open data/ with relative paths
sys.path.insert(0, str(ROOT))

os.environ["ANTHROPIC_API_KEY"] = "offline-test"
os.environ["VOYAGE_API_KEY"] = "offline-test"
os.environ.pop("ATLAS_TRACING", None)

QUERY_VECTORS = json.loads((ROOT / "tests/fixtures/query_vectors.json").read_text())


class _Embeddings:
    def __init__(self, embeddings):
        self.embeddings = embeddings


class FakeVoyage:
    def __init__(self, *args, **kwargs):
        self.calls = []

    def embed(self, texts, model=None, **kwargs):
        self.calls.append(list(texts))
        return _Embeddings([self.vector(t) for t in texts])

    @staticmethod
    def vector(text):
        if text in QUERY_VECTORS:
            return QUERY_VECTORS[text]
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        return np.random.default_rng(seed).normal(size=1024).tolist()


import voyageai  # noqa: E402

voyageai.Client = FakeVoyage

import anthropic  # noqa: E402


def message(*blocks, stop_reason=None, input_tokens=100, output_tokens=20):
    """Build a real anthropic Message from text strings and tool_use dicts."""
    content = [{"type": "text", "text": b} if isinstance(b, str) else b for b in blocks]
    if stop_reason is None:
        stop_reason = "tool_use" if any(b["type"] == "tool_use" for b in content) else "end_turn"
    return anthropic.types.Message.model_validate({
        "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-haiku-4-5",
        "content": content, "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    })


def tool_use(name, tool_input, id="toolu_1"):
    return {"type": "tool_use", "id": id, "name": name, "input": tool_input}


class FakeAnthropic:
    """script = {"classify": [...], "generate": [...], "verify": [...]}; each item is a
    Message, a string (wrapped as a text Message) or a callable(kwargs) -> Message."""

    def __init__(self, script):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls = []
        self.messages = self

    @staticmethod
    def purpose(kwargs):
        if "tools" in kwargs:
            return "generate"
        return {10: "classify", 100: "verify"}.get(kwargs["max_tokens"], "other")

    def create(self, **kwargs):
        purpose = self.purpose(kwargs)
        self.calls.append((purpose, json.loads(json.dumps(kwargs, default=str))))
        queue = self.script.get(purpose)
        if not queue:
            raise AssertionError(f"unexpected {purpose} call")
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if callable(item):
            item = item(kwargs)
        return message(item) if isinstance(item, str) else item

    def calls_for(self, purpose):
        return [kw for p, kw in self.calls if p == purpose]


@pytest.fixture
def fake_llm(monkeypatch):
    """Install a FakeAnthropic on src.agent. Call it with a script."""
    import src.agent

    def install(**script):
        fake = FakeAnthropic(script)
        monkeypatch.setattr(src.agent, "client", fake)
        return fake

    return install


class _Text:
    def __init__(self, text):
        self.text = text


class _Result:
    def __init__(self, text, is_error=False):
        self.content = [_Text(text)]
        self.isError = is_error


class FakeSession:
    """Stand-in for an MCP ClientSession that calls the tool functions directly."""

    def __init__(self):
        self.calls = []

    async def call_tool(self, name, arguments):
        from src.tools import get_customer_orders, get_order_status

        self.calls.append((name, arguments))
        fn = {"get_order_status": get_order_status, "get_customer_orders": get_customer_orders}[name]
        return _Result(json.dumps(fn(**arguments)))


@pytest.fixture
def session():
    return FakeSession()


@pytest.fixture
def anyio_backend():
    return "asyncio"
