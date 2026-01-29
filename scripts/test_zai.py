import os
import sys
from openai import OpenAI

BASE = "https://api.z.ai/api/paas/v4/"
KEY = os.environ.get("ZAI_API_KEY")

if not KEY:
    try:
        with open('.env') as f:
            for line in f:
                if line.startswith('ZAI_API_KEY='):
                    KEY = line.split('=')[1].strip()
                    break
    except:
        pass

if not KEY:
    print("❌ ZAI_API_KEY not found")
    sys.exit(1)

# Testing Flash/Free variants
candidates = [
    "glm-4-flash",
    "glm-4-flashx", 
    "glm-4.7-flash",
    "GLM-4-Flash", # Case check
    "glm-zero-preview",
    "glm-4-airx",
    "glm-4-0520",
    "glm-4-assist"
]

print(f"Testing Free/Flash Models on {BASE}")
print("-" * 50)

client = OpenAI(api_key=KEY, base_url=BASE)

for model in candidates:
    print(f"Testing '{model}'...", end=" ")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        print("✅ SUCCESS!")
        print(f"Response: {resp.choices[0].message.content}")
        print(f"🎉 VALID FREE MODEL: {model}")
        break # Stop on first success
    except Exception as e:
        msg = str(e)
        if "1211" in msg or "not exist" in msg:
            print("❌ Invalid")
        elif "1113" in msg:
            print("💰 Insufficient Balance (Valid but paid)")
        else:
            print(f"❌ Error: {msg[:50]}...")
