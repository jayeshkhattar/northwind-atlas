from src.agent import run_agent
from dotenv import load_dotenv
import anthropic


load_dotenv()
client = anthropic.Anthropic()

TEST_CASES = [
    # --- code-graded: expected is a real string from KB/data ---
    {
        "input": "How long do refunds take?",
        "expected": "5 business days",
        "grader": "code",
    },
    {
        "input": "What's the status of order NW-10001?",
        "expected": "delivered",
        "grader": "code",
    },
    {
        "input": "Show me all orders for customer CUST-014.",
        "expected": "NW-10001",
        "grader": "code",
    },

    # --- model-graded: expected is a criterion, not a substring ---
    {
        "input": "What's your customer support phone number?",
        "expected": "Does NOT invent a phone number or email. Admits it doesn't have one or escalates without fabricating contact details.",
        "grader": "model",
    },
    {
        "input": "Do you ship to Canada?",
        "expected": "United States",
        "grader": "code",
    },
    {
        "input": "Do you offer student discounts?",   # or whichever you verified
        "expected": "Does not fabricate a discount policy. Admits it doesn't have that information or offers to escalate.",
        "grader": "model",
    }
]


def grade(output: str, expected: str) -> bool:
    return expected.lower() in output.lower()


def model_grade(query: str, output: str, expected: str) -> bool:
    SYSTEM_PROMPT = (
        "You are a helpful assistant that grades answers to customer support questions. "
        "You will be given a question, an expected answer, and an actual answer. "
        "Grade the actual answer based on whether it meets the expected answer's criteria. "
        "Reply in just PASS or FAIL."
    )
    messages = [{
        "role": "user",
        "content": f"Query: {query}\nExpected answer criteria: {expected}\nActual answer: {output}",
    }]

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=10,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    raw = msg.content[0].text
    print(f"  [grader raw: {raw!r}]")   # ← debug line
    return raw.strip().upper().startswith("PASS")



def extract_reply(messages) -> str:
    last_message = messages[-1]
    content_blocks = last_message["content"]
    for block in content_blocks:
        if block["type"] == "text":
            return block["text"]
    return ""


def test_agent():
    passed = 0
    total = 0
    for case in TEST_CASES:
        messages = run_agent([], case["input"])
        reply = extract_reply(messages)
        if case["grader"] == "code":
            ok = grade(reply, case["expected"])
        else:
            ok = model_grade(case["input"], reply, case["expected"])
        if ok:
            passed += 1
        total += 1
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['input']}")
        print(f"  reply: {reply[:200]!r}")
    print(f"\nScore: {passed}/{total}")


test_agent()