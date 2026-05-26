import os
import sys
import time
from openai import OpenAI

# Load Key
KEY = os.environ.get("ZAI_API_KEY")
if not KEY:
    try:
        with open('.env') as f:
            for line in f:
                if line.startswith('ZAI_API_KEY='):
                    KEY = line.split('=')[1].strip()
                    break
    except Exception:
        pass

if not KEY:
    print("❌ ZAI_API_KEY not found")
    sys.exit(1)

BASE = "https://api.z.ai/api/paas/v4/"
MODEL = "glm-4.7-flash"

print(f"📡 Connecting to: {BASE}")
print(f"🤖 Model: {MODEL}")
print("-" * 50)

client = OpenAI(api_key=KEY, base_url=BASE)

# 1. Test Small Payload (Ping)
print("\n[1/2] Testing Small Payload (Ping)...")
start = time.time()
try:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=5
    )
    duration = time.time() - start
    print(f"✅ Success! Duration: {duration:.2f}s")
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)

# 2. Test Large Payload (Context Simulation)
# Watcher sends ~14k chars of context
print("\n[2/2] Testing Large Payload (~15k characters)...")
LARGE_CONTEXT = "test context " * 2000 # Approx 14k chars
start = time.time()

try:
    print("   Sending request...")
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": f"You are a code reviewer. Context:\n{LARGE_CONTEXT}"},
            {"role": "user", "content": "Review this code: function test() { return true; }"}
        ],
        max_tokens=500
    )
    duration = time.time() - start
    print(f"✅ Success! Duration: {duration:.2f}s")
    print(f"Characters received: {len(resp.choices[0].message.content)}")
except Exception as e:
    print(f"❌ Failed: {e}")
