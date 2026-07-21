#from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing import TypedDict
from .agent import SYSTEM_PROMPT, build_context, tool_loop, extract_reply
from .tools import get_order_status, get_customer_orders, GET_ORDER_STATUS_SCHEMA, GET_CUSTOMER_ORDERS_SCHEMA

TOOL_FUNCTIONS = {
    "get_order_status": get_order_status,
    "get_customer_orders":get_customer_orders,
}

cl_model_name = "claude-haiku-4-5"
op_model_name = 'openai/gpt-4o'

load_dotenv()

FALLBACK_TEXT = """I'm not able to confirm this from our information.
    Let me escalate you to a human agent who can help."""

# llm = ChatAnthropic(model=cl_model_name, max_tokens=100)
# response = llm.invoke([HumanMessage(content="Say hello in 3 words")])
# print(response.content)

llm = ChatOpenAI(model=op_model_name, 
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    )
llm = llm.bind_tools([get_order_status, get_customer_orders])

class AgentState(TypedDict):
    query: str          # — the question
    messages: list      # — conversation history
    route: str          # — KB/TOOL/BOTH
    context: str        # — retrieved KB
    answer: str         # — generated reply
    grounding: str      # — context + tool results for verify
    passed: bool        # — verify verdict
    reason: str         # — verify failure reason
    attempt: int        # — retry counter

def classify(state: AgentState) -> dict:
    query = state["query"]
    message = f"""You are a query classifier for a coffee-gear support agent.
    Classify this query: {query} into exactly one word: KB, TOOL, or BOTH.
    - KB: answerable from support docs (policies, shipping, returns, product info)
    - TOOL: needs live order status or customer account data
    - BOTH: needs docs AND live data
    Reply with exactly one word. Do not explain."""
    response = llm.invoke([HumanMessage(content=message)])
    route = response.content.strip().upper()
    return {"route": route}

def retrieve(state: AgentState) -> dict:
    if state["route"] in ("KB", "BOTH"):
        context = build_context(state["query"])
    else:
        context = ""
    return {"context": context}

def generate(state: AgentState) -> dict:
    system = SYSTEM_PROMPT + (f"\n\nDocs:\n{state['context']}" if state["context"] else "")
    if state["reason"]:
        system += f"\n\nPrevious answer failed grounding: {state['reason']}. State only facts in the context."
    messages = [SystemMessage(content=system), HumanMessage(content=state["query"])]
    tool_outputs = []
    while True:
        response = llm.invoke(messages)
        messages.append(response)
        if response.tool_calls:
            for call in response.tool_calls:
                fn = TOOL_FUNCTIONS[call["name"]]
                result = fn(**call["args"])
                tool_outputs.append(str(result))
                messages.append(ToolMessage(content=str(result), tool_call_id = call["id"]))
        else:
            ground_message = f"KB Context:\n{state['context']}\nTOOL RESULT:\n{chr(10).join(tool_outputs)}"
            return {"answer": response.content, "grounding": ground_message, "messages":messages}

def verify(state: AgentState) -> dict:
    message = f"""You are a verifier for a coffee-gear support agent.
    Check if answer is supported by the grounding
    - query: {state['query']}
    - Grounding: {state['grounding']}
    - Answer: {state['answer']}
    Reply PASS if grounded. If not, reply FAIL: <one-line reason>."""
    response = llm.invoke([HumanMessage(content=message)])
    passed = response.content.strip().upper().startswith("PASS")
    reason = "" if passed else response.content
    attempt = state["attempt"]
    if passed == False:
        attempt += 1 
    return {"passed":passed, "reason":reason, "attempt": attempt}

def after_verify(state: AgentState):
    if state["passed"]:
        return END
    if state["attempt"] >= 2:
        return "fallback"
    return "generate"

def fallback(state: AgentState) -> dict:
    return {"answer":FALLBACK_TEXT}

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("classify", classify)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_node("verify", verify)
    graph.add_node("fallback", fallback)
    graph.set_entry_point("classify")
    graph.add_edge("classify", "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "verify")
    graph.add_conditional_edges("verify", after_verify)
    graph.add_edge("fallback", END)
    return graph.compile()

if __name__ == "__main__":
    base = {"query":"", "messages":[], "route":"", "context":"", "answer":"",
                "grounding":"", "passed":False, "reason":"", "attempt":0}
    app = build_graph()
    result = app.invoke({**base, "query": "how long do refunds take"})
    print(result["answer"])