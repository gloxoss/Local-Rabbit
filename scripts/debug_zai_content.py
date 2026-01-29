import os
import sys
from openai import OpenAI

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

BASE = "https://api.z.ai/api/paas/v4/"
MODEL = "glm-4.7-flash"

print(f"📡 Connecting to: {BASE}")
print(f"🤖 Model: {MODEL}")

# The exact content of test.js
CODE = "function hello() { return 'world'; }"

SYSTEM_PROMPT = "You are a code reviewer. Review the code concisely."

USER_PROMPT = f"Please review this code (test.js):\n```\n{CODE}\n```"

print("-" * 50)
print("Sending request...")

client = OpenAI(api_key=KEY, base_url=BASE)

try:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': USER_PROMPT}
        ],
        max_tokens=1000
    )
    content = resp.choices[0].message.content
    
    if not content:
        print("❌ RECEIVED EMPTY RESPONSE")
    else:
        print("✅ SUCCESS!")
        print(content)
        
except Exception as e:
    print(f"❌ ERROR: {e}")
