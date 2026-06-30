from dotenv import load_dotenv
import anthropic
from src.retrieval import load_kb, build_tokens, get_bm, search
from src.tools import get_order_status, get_customer_orders, GET_ORDER_STATUS_SCHEMA, GET_CUSTOMER_ORDERS_SCHEMA

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
    hits = search(query, chunks, bm25)
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

def run_agent(query):
    messages = [{"role": "user", "content": query}]

    while True:
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            tools=[GET_ORDER_STATUS_SCHEMA, GET_CUSTOMER_ORDERS_SCHEMA],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": msg.content})
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
            return msg.content[0].text

#run_agent("where is my order NW-10001?")
print(run_agent("what are the orders for CUST-007?"))

