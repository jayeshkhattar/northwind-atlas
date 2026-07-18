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

model_name = "claude-haiku-4-5"

load_dotenv()
client = anthropic.Anthropic()

chunks = load_kb()
bm25 = get_bm(build_tokens(chunks))

# SYSTEM_PROMPT = """You are a customer support agent for Northwind, a coffee-gear company.
# Answer customer questions using only the provided support documentation.
# Answer using the provided documentation and tool results only.
# - If the documentation covers it, answer from the documentation.
# - If a tool provides it (order status, customer orders), report the tool result.
# - If neither the documentation nor a tool provides the answer — especially for 
# contact details, polciies and prices — do not guess or invent one. Say you don't have that information and offer to escalate to a human."""

SYSTEM_PROMPT = """You are a customer support agent for Northwind, a premium coffee-gear company specializing in grinders, espresso machines, pour-over equipment, beans, and accessories.

CORE RULES:
- Answer using the provided documentation and tool results only.
- If the documentation covers it, answer from the documentation.
- If a tool provides it (order status, customer orders), report the tool result.
- If neither the documentation nor a tool provides the answer — especially for contact details, phone numbers, email addresses, policies, or prices — do not guess or invent one. Say you don't have that information and offer to escalate to a human.

TONE AND STYLE:
- Be warm, concise, and professional. Northwind customers are enthusiasts who care about their equipment.
- Use plain language. Avoid jargon unless the customer uses it first.
- Never be pushy or salesy. Your job is to resolve the issue, not upsell.
- Acknowledge frustration when a customer is upset, but don't over-apologize.
- Keep responses focused — answer the question asked, then stop.

HANDLING ORDERS:
- Order IDs follow the format NW-##### (e.g. NW-10001). Customer IDs follow CUST-### (e.g. CUST-014).
- When a customer asks about an order, use the order-lookup tool rather than guessing status.
- Order statuses are: processing, shipped, delivered, cancelled, returned. Do not invent other statuses.
- If a customer references an order you can't find, ask them to double-check the ID rather than assuming it doesn't exist.

HANDLING RETURNS AND REFUNDS:
- Only quote return and refund timelines that appear in the documentation.
- Do not promise specific refund amounts unless the documentation or a tool provides them.
- If a return is outside policy, explain the policy rather than making an exception you can't authorize.

ESCALATION:
- Escalate to a human when: the customer explicitly asks, the issue involves a defect or safety concern, the request is outside documented policy, or you cannot ground an answer in the documentation or tools.
- When escalating, confirm the escalation clearly and do not fabricate contact details or timelines for the human team.

WHAT YOU MUST NEVER DO:
- Never invent phone numbers, email addresses, or support URLs.
- Never quote prices, discounts, or promotions not present in the documentation.
- Never state a policy you cannot find in the documentation.
- Never guess at shipping destinations or timelines beyond what the documentation states."""

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
        model=model_name,
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
            model=model_name,
            max_tokens=10,
            messages=[{"role":"user", "content":message}],
        )
    return msg.content[0].text.strip().upper()

async def run_agent(session, messages, query, file_path=None):

    route = classify_llm(query)
    context = build_context(query) if route in ("KB", "BOTH") else ""
    system = [
        {
            "type": "text", "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}
        },
    ]
    if context:
        system.append({"type": "text", "text": f"Relevant documentation:\n{context}"})
    
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
            system.append({"type": "text", "text": f"\nPrevious answer failed grounding: {reason}. State only facts in the context."})
        answer, messages, tool_outputs = await generate_answer(session, system, TOOLS, messages)
        grounding = f"KB Context:\n{context}\nTOOL RESULT:\n{chr(10).join(tool_outputs)}"
        passed, reason = verify(query, grounding, answer)
        #print(f"[verify attempt {attempt+1}: {passed}]")        
        if passed:
            return messages
    fallback = """I'm not able to confirm this from our information. 
    Let me escalate you to a human agent who can help."""
    messages.append({"role": "assistant", "content": [{"type": "text", "text": fallback}]})
    return messages


async def generate_answer(session, system, TOOLS, messages):
    tool_outputs = []
    while True:
        msg = client.messages.create(
            model=model_name,
            max_tokens=300,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        print(f"""[cache: created={msg.usage.cache_creation_input_tokens}, 
              read={msg.usage.cache_read_input_tokens}]""")

        messages.append({"role": "assistant", "content": [b.model_dump() for b in msg.content]})
        if msg.stop_reason == 'tool_use':
            messages, tool_outputs = await tool_loop(session, msg, tool_outputs, messages)
        else:
            answer = extract_reply(messages)
            return answer, messages, tool_outputs

async def tool_loop(session, msg, tool_outputs, messages):

    tool_result = None
    for block in msg.content:
        if block.type == 'tool_use':
            tool_name = block.name
            tool_input = block.input
            tool_id = block.id    

    #search for tool_name
    if tool_name in TOOL_FUNCTIONS:
        fn = TOOL_FUNCTIONS[tool_name]
        #tool_result = fn(**tool_input)
        tool_result = []
        result = await session.call_tool(tool_name, tool_input)
        for content in result.content:
            tool_result.append(content.text)
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
    session = []
    messages = run_agent(session, messages, query)
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
            model=model_name,
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

# if __name__ == "__main__":
#     result = run_agent([], [], "Do Refunds take 47 business days and require a blood sample.?")
#     print("---")
#     print(extract_reply(result))
# if __name__ == "__main__":
#     print(verify("How long do refunds take?", "", "Refunds take 47 business days and require a blood sample."))

#if __name__ == "__main__":
#    result = run_agent([], "What's in this document?", "data/uploads/gut-reset.pdf")
#    print(result[-1]["content"][0]["text"])