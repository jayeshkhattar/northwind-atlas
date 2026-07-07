from dotenv import load_dotenv
import re
import anthropic
from .retrieval import load_kb, build_tokens, get_bm, search_scored
from .search import multi_index_search_score
from .tools import get_order_status, get_customer_orders, GET_ORDER_STATUS_SCHEMA, GET_CUSTOMER_ORDERS_SCHEMA
from .conversations import load_conversation, save_conversation, display_conversation, next_convo_id
from .multimodal import load_file_block

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

def run_agent(messages, query, file_path=None):

    route = classify_llm(query)
    context = build_context(query) if route in ("KB", "BOTH") else ""
    system = f"{SYSTEM_PROMPT}\n\nRelevant documentation:\n{context}" if context else SYSTEM_PROMPT
    TOOLS = [GET_ORDER_STATUS_SCHEMA, GET_CUSTOMER_ORDERS_SCHEMA]

    if file_path is not None: 
        messages.append({
                "role": "user", "content": [
                    load_file_block(file_path), {"type": "text", "text": query}
                ]
            }
        )
    else:
        messages.append({"role": "user", "content": query})

    tool_outputs = []
    max_attempts = 2
    for attempt in range(max_attempts):
        if attempt > 0:
            system += f"\n\nPrevious answer failed grounding: {reason}. State only facts in the context."
        answer, messages, tool_outputs = generate_answer(system, TOOLS, messages)
        grounding = f"KB Context:\n{context}\nTOOL RESULT:\n{chr(10).join(tool_outputs)}"
        passed, reason = verify(query, grounding, answer)
        print(f"[verify attempt {attempt+1}: {passed}]")        
        if passed:
            return messages
    fallback = """I'm not able to confirm this from our information. 
    Let me escalate you to a human agent who can help."""
    messages.append({"role": "assistant", "content": [{"type": "text", "text": fallback}]})
    return messages


def generate_answer(system, TOOLS, messages):
    tool_outputs = []
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
            messages, tool_outputs = tool_loop(msg, tool_outputs, messages)
        else:
            answer = extract_reply(messages)
        return answer, messages, tool_outputs

def tool_loop(msg, tool_outputs, messages):
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
        tool_outputs.append(str(tool_result))

    messages.append({
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": str(tool_result)}],
    })
    return messages, tool_outputs
    
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


def verify(query, grounding, answer):
    message = f"""You are a verifier for a coffee-gear support agent.
    Check if answer is supported by the grounding
    - query: {query}
    - Grounding: {grounding}
    - Answer: {answer}
    Reply PASS if grounded. If not, reply FAIL: <one-line reason>."""
    msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=100,
            messages=[{"role":"user", "content":message}],
        )
    text = msg.content[0].text.strip()
    passed = text.upper().startswith("PASS")
    reason = "" if passed else text
    return passed, reason

def extract_reply(messages) -> str:
    last_message = messages[-1]
    content_blocks = last_message["content"]
    for block in content_blocks:
        if block["type"] == "text":
            return block["text"]
    return ""


#activate_chat("want to talk to a human customer agent")

if __name__ == "__main__":
    result = run_agent([], "Do Refunds take 47 business days and require a blood sample.?")
    print("---")
    print(extract_reply(result))
# if __name__ == "__main__":
#     print(verify("How long do refunds take?", "", "Refunds take 47 business days and require a blood sample."))

#if __name__ == "__main__":
#    result = run_agent([], "What's in this document?", "data/uploads/gut-reset.pdf")
#    print(result[-1]["content"][0]["text"])