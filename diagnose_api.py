import anthropic
import json

import os
key = os.environ.get("ANTHROPIC_API_KEY", "your_anthropic_api_key_here")
client = anthropic.Anthropic(api_key=key)

try:
    print("Testing connection with Haiku...")
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=10,
        messages=[{"role": "user", "content": "hi"}]
    )
    print("SUCCESS!")
    print(response.content[0].text)
except anthropic.BadRequestError as e:
    print(f"FAILED: BadRequestError")
    print(json.dumps(e.body, indent=2))
except Exception as e:
    print(f"FAILED: {type(e).__name__}")
    print(e)
