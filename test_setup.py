from dotenv import load_dotenv
import anthropic

load_dotenv()
client = anthropic.Anthropic()          # reads ANTHROPIC_API_KEY automatically
msg = client.messages.create(
    model="claude-sonnet-4-6",          # current Sonnet — the build's workhorse
    max_tokens=50,
    messages=[{"role": "user", "content": "Reply with exactly: setup works"}],
)
print(msg.content[0].text)