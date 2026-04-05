import openai
import json

import os
key = os.environ.get("OPENROUTER_API_KEY", "your_openrouter_api_key_here")
client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=key,
)

try:
    print("Testing OpenRouter with qwen/qwen-2-7b-instruct:free...")
    response = client.chat.completions.create(
        model="qwen/qwen-2-7b-instruct:free",
        messages=[{"role": "user", "content": "hi"}],
        extra_headers={
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Diagnostic",
        }
    )
    print("SUCCESS!")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"FAILED: {type(e).__name__}")
    if hasattr(e, 'response'):
        print(f"Response: {e.response.text}")
    print(f"Error: {e}")
