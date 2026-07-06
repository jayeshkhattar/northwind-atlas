from dotenv import load_dotenv
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
If the documentation doesn't contain the answer, say you don't have that information and offer to escalate to a human.
Be concise, friendly, and direct. Do not invent policies."""


def build_context(query):
    hits = multi_index_search_score(query)
    blocks = [
        f"{hit['source']} > {hit['heading']} > {hit['text']}"
        for hit in hits
    ]
    return "\n\n".join(blocks)

def send_to_claude(query):
    blocks = build_context(query)
    prompt = f"context: {blocks}\n\nquery: {query}"
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

def run_agent(messages, query):

    context = build_context(query)
    system = f"{SYSTEM_PROMPT}\n\nRelevant documentation:\n{context}" # ← add: inject

    messages.append({"role": "user", "content": query})

    while True:
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            system=system,
            tools=[GET_ORDER_STATUS_SCHEMA, GET_CUSTOMER_ORDERS_SCHEMA],
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

#activate_chat("want to talk to a human customer agent", 3)
