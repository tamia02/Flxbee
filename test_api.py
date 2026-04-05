import anthropic
import os

import os
key = os.environ.get("ANTHROPIC_API_KEY", "your_anthropic_api_key_here")
client = anthropic.Anthropic(api_key=key)

try:
    print("Testing connection...")
    response = client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=10,
        messages=[{"role": "user", "content": "Hello"}]
    )
    print("SUCCESS!")
    print(response.content[0].text)
except Exception as e:
    print(f"FAILED: {type(e).__name__}")
    print(e)
