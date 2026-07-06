import json
import os

def load_conversation(conversation_id):
    path = f"data/conversations/{conversation_id}.json"
    if os.path.exists(path):
        with open(path) as file:
            return json.load(file)
    return []

def save_conversation(conversation_id, messages):
    path = f"data/conversations/{conversation_id}.json"
    with open(path, "w") as f:
        json.dump(messages, f)

def display_conversation(messages):
    for m in messages:
        role = m["role"]
        content = m["content"]

        if role == "user" and isinstance(content, str):
            # real customer message
            print("You:", content)

        elif role == "assistant":
            # content is a list of blocks — show only text blocks
            for block in content:
                if block["type"] == "text":
                    print("AI:", block["text"])


def next_convo_id():
    folder = "data/conversations"
    files = os.listdir(folder)
    highest = -1
    for f in files:
        if not f.endswith(".json"):
            continue
        num = int(f.replace(".json", ""))
        if num > highest:
            highest = num
    return highest+1

