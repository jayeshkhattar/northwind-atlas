"""Streamlit demo UI for the Northwind support agent.

Run from the repo root (relative data paths and `python -m src.mcp_server` require it):

    streamlit run src/ui.py
"""
import asyncio
import os
import sys
import threading
from contextlib import AsyncExitStack

# `streamlit run src/ui.py` puts this file's dir (src/) on sys.path, not the repo
# root — so `import src.*` fails. Add the repo root (parent of src/) explicitly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.agent import run_agent
from src.conversations import load_conversation, save_conversation

CONVO_DIR = "data/conversations"
UPLOAD_DIR = "data/uploads"
SERVER_PARAMS = StdioServerParameters(command="python", args=["-m", "src.mcp_server"])


# ---------------------------------------------------------------- MCP bridge
class MCPBridge:
    """Keeps one MCP subprocess + session alive on a background event loop,
    so each message skips the ~1-2s subprocess spawn."""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.session = None
        self._submit(self._start()).result(timeout=30)

    def _submit(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    async def _start(self):
        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(SERVER_PARAMS))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    def run(self, coro_fn, timeout=120):
        """coro_fn: session -> coroutine. Runs it on the bridge's loop."""
        return self._submit(coro_fn(self.session)).result(timeout=timeout)


@st.cache_resource(show_spinner=False)
def get_bridge():
    return MCPBridge()


def send(messages, query, file_path):
    """Run one agent turn over the persistent MCP session. Returns (messages, signals).
    If the cached session died (stale subprocess), rebuild it once and retry."""
    signals = {}

    def _turn(session):
        return run_agent(session, messages, query, file_path, signals)

    try:
        return get_bridge().run(_turn), signals
    except Exception:
        get_bridge.clear()  # drop the dead bridge, spawn a fresh one
        signals.clear()
        return get_bridge().run(_turn), signals


# ---------------------------------------------------------------- persistence
def list_convo_ids():
    if not os.path.isdir(CONVO_DIR):
        return []
    ids = []
    for name in os.listdir(CONVO_DIR):
        if name.endswith(".json"):
            stem = name[: -len(".json")]
            if stem.isdigit():
                ids.append(int(stem))
    return sorted(ids)


def new_convo_id():
    # Local variant of conversations.next_convo_id() that tolerates non-integer filenames.
    ids = list_convo_ids()
    return max(ids) + 1 if ids else 0


# ---------------------------------------------------------------- rendering
CSS = """
<style>
/* tighten the page + soften bubbles */
.block-container { max-width: 46rem; padding-top: 2.5rem; }
[data-testid="stChatMessage"] {
    border-radius: 14px;
    padding: 0.6rem 0.9rem;
    margin-bottom: 0.35rem;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: rgba(99, 110, 250, 0.09);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: rgba(128, 128, 128, 0.07);
}
.nw-pills { margin: 0 0 0.35rem 0; line-height: 1.9; }
.nw-pill {
    display: inline-block;
    padding: 1px 10px;
    margin-right: 6px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    border: 1px solid;
    white-space: nowrap;
}
</style>
"""

PILL_COLORS = {
    "route": "#4c8bf5",   # blue
    "pass": "#2eb872",    # green
    "fail": "#e5484d",    # red
    "cache": "#d29922",   # amber
    "tool": "#9a6dd7",    # purple
}


def pill(text, kind):
    c = PILL_COLORS[kind]
    return (
        f'<span class="nw-pill" style="color:{c};border-color:{c}55;'
        f'background:{c}1a">{text}</span>'
    )


def render_signals(signals):
    if not signals:
        return
    pills = []
    if signals.get("route"):
        pills.append(pill(f"route · {signals['route']}", "route"))

    attempts = signals.get("verify") or []
    if attempts:
        last = attempts[-1]
        if last["passed"]:
            pills.append(pill(f"verify · pass (attempt {last['attempt']})", "pass"))
        else:
            pills.append(pill(f"verify · fail ×{len(attempts)}", "fail"))

    cache = signals.get("cache") or {}
    if cache.get("created") or cache.get("read"):
        pills.append(pill(f"cache · {cache.get('created', 0)}w / {cache.get('read', 0)}r", "cache"))

    for tool in signals.get("tools") or []:
        pills.append(pill(f"⚙ {tool}", "tool"))

    if pills:
        st.markdown(f'<div class="nw-pills">{"".join(pills)}</div>', unsafe_allow_html=True)
    if signals.get("fallback"):
        st.warning("Grounding failed twice — escalated to a human agent.", icon="🚨")
    attempts_failed = [a for a in attempts if not a["passed"]]
    if attempts_failed:
        with st.expander("verify failure reasons"):
            for a in attempts_failed:
                st.caption(f"attempt {a['attempt']}: {a.get('reason') or 'ungrounded'}")


def text_of(blocks):
    return "\n".join(b["text"] for b in blocks if b.get("type") == "text")


def render_user(content):
    """User turns are either a plain string or a block list (file upload / tool_result)."""
    if isinstance(content, str):
        with st.chat_message("user"):
            st.markdown(content)
        return

    kinds = {b.get("type") for b in content}
    if "tool_result" in kinds:
        return  # internal plumbing, not a customer message

    with st.chat_message("user"):
        for block in content:
            if block.get("type") == "image":
                st.caption("🖼️ image attached")
            elif block.get("type") == "document":
                st.caption("📄 document attached")
        text = text_of(content)
        if text:
            st.markdown(text)


def render_history():
    for i, m in enumerate(st.session_state.messages):
        if m["role"] == "user":
            render_user(m["content"])
        else:
            text = text_of(m["content"])
            if not text:
                continue  # tool_use-only turn
            with st.chat_message("assistant"):
                render_signals(st.session_state.signals_by_turn.get(i))
                st.markdown(text)


# ---------------------------------------------------------------- app
st.set_page_config(page_title="Northwind Support", page_icon="☕")
st.markdown(CSS, unsafe_allow_html=True)

if "convo_id" not in st.session_state:
    st.session_state.convo_id = new_convo_id()
    st.session_state.messages = []
    st.session_state.signals_by_turn = {}

with st.sidebar:
    st.header("☕ Northwind")
    if st.button("➕ New chat", use_container_width=True):
        st.session_state.convo_id = new_convo_id()
        st.session_state.messages = []
        st.session_state.signals_by_turn = {}
        st.rerun()

    ids = list_convo_ids()
    if ids:
        current = st.session_state.convo_id
        options = sorted(set(ids + [current]))
        picked = st.selectbox("Conversation", options, index=options.index(current))
        if picked != st.session_state.convo_id:
            st.session_state.convo_id = picked
            st.session_state.messages = load_conversation(picked)
            st.session_state.signals_by_turn = {}
            st.rerun()

    st.caption(f"conversation #{st.session_state.convo_id}")
    st.divider()
    uploaded = st.file_uploader("Attach a file", type=["png", "jpg", "jpeg", "pdf"])

st.title("Northwind Support")
if not st.session_state.messages:
    st.caption("Ask about orders (NW-#####), returns, shipping, or attach a receipt.")
render_history()

query = st.chat_input("Ask about an order, a return, shipping…")
if query:
    file_path = None
    if uploaded is not None:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, uploaded.name)
        with open(file_path, "wb") as f:
            f.write(uploaded.getbuffer())

    # echo the user's message immediately, then think
    with st.chat_message("user"):
        if file_path:
            st.caption(f"📎 {uploaded.name}")
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Routing → retrieving → verifying…"):
            messages, signals = send(st.session_state.messages, query, file_path)

    st.session_state.messages = messages
    st.session_state.signals_by_turn[len(messages) - 1] = signals
    save_conversation(st.session_state.convo_id, messages)
    st.rerun()
