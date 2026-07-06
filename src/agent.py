from dotenv import load_dotenv
import re
import anthropic
from .retrieval import load_kb, build_tokens, get_bm, search_scored
from .search import multi_index_search_score
from .tools import get_order_status, get_customer_orders, GET_ORDER_STATUS_SCHEMA, GET_CUSTOMER_ORDERS_SCHEMA
from .conversations import load_conversation, save_conversation, display_conversation, next_convo_id
TOOL_FUNCTIONS = {
    "get_order_status": get_order_status,
    "get_customer_orders":get_customer_orders,
}


load_dotenv()
client = anthropic.Anthropic()

chunks = load_kb()
bm25 = get_bm(build_tokens(chunks))

SYSTEM_PROMPT = """You are a customer support agent for Northwind, a coffee-gear company.
Answer customer questions using only the provided support documentation.
Answer using the provided documentation and tool results only.
- If the documentation covers it, answer from the documentation.
- If a tool provides it (order status, customer orders), report the tool result.
- If neither the documentation nor a tool provides the answer — especially for 
contact details, polciies and prices — do not guess or invent one. Say you don't have that information and offer to escalate to a human."""


def build_context(query):
    hits = multi_index_search_score(query)
    blocks = [
        f"{hit['source']} > {hit['heading']} > {hit['text']}"
        for hit in hits
    ]
    return "\n\n".join(blocks)

def classify(query):
    if re.search(r"(NW|CUST)-\d+", query):
        return "tool"
    else:
        return "KB"

def send_to_claude(query):
    context = build_context(query)
    prompt = f"context: {context}\n\nquery: {query}"
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return msg.content[0].text

# query1 = "how long do refunds take"
# query2 = "do you ship to Canada?"
# print(send_to_claude(query1))
# print(send_to_claude(query2))

def classify_llm(query):
    message = f"""You are a query classifier for a coffee-gear support agent.
    Classify this query: {query} into exactly one word: KB, TOOL, or BOTH.
    - KB: answerable from support docs (policies, shipping, returns, product info)
    - TOOL: needs live order status or customer account data
    - BOTH: needs docs AND live data
    Reply with exactly one word. Do not explain."""
    msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=10,
            messages=[{"role":"user", "content":message}],
        )
    return msg.content[0].text.strip().upper()

def run_agent(messages, query):
    #route = classify(query)
    route = classify_llm(query)
    print(f"[route: {route}]")   # temporary — see the decision
    if route == ("KB", "BOTH"):
        context = build_context(query)
    else:
        context = ""

    if context:
        system = f"{SYSTEM_PROMPT}\n\nRelevant documentation:\n{context}" # ← add: inject
    else:
        system = SYSTEM_PROMPT

    TOOLS = [GET_ORDER_STATUS_SCHEMA, GET_CUSTOMER_ORDERS_SCHEMA]
    messages.append({"role": "user", "content": query})

    while True:
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": [b.model_dump() for b in msg.content]})
        if msg.stop_reason == 'tool_use':
            tool_result = None
            for block in msg.content:
                if block.type == 'tool_use':
                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id    

            #search for tool_name
            if tool_name in TOOL_FUNCTIONS:
                fn = TOOL_FUNCTIONS[tool_name]
                tool_result = fn(**tool_input)

            messages.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": str(tool_result)}],
            })
        else:
            return messages

def activate_chat(query, convo_id=-1):
    if convo_id == -1:
        convo_id = next_convo_id()
        messages = []
    else:
        messages = load_conversation(convo_id)
    display_conversation(messages)
    before = len(messages)
    messages = run_agent(messages, query)
    display_conversation(messages[before:]) # show ONLY the new messages
    save_conversation(convo_id, messages)

#activate_chat("want to talk to a human customer agent")
