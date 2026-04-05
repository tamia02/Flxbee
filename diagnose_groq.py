import openai

import os
key = os.environ.get("GROQ_API_KEY", "your_groq_api_key_here")
client = openai.OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=key,
)

models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama3-70b-8192", "llama3-8b-8192"]

for model in models:
    try:
        print(f"Testing Groq with {model}...")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
        )
        print(f"SUCCESS with {model}!")
        print(response.choices[0].message.content)
        break
    except Exception as e:
        print(f"FAILED with {model}: {e}")
