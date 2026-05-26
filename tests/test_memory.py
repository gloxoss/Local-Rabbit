import requests
import json
import time

def test_memory():
    # 1. Send a message via Chat Stream (which logs to DB)
    url_stream = "http://localhost:8765/api/chat/stream"
    payload = {
        "query": "Hello Memory!",
        "context": {
            "project_root": "c:/Users/zakio/Desktop/Work/Local Rabbit"
        }
    }
    
    print("🌊 Sending Chat Message...")
    try:
        with requests.post(url_stream, json=payload, stream=True) as r:
            for _ in r.iter_lines(): pass # Consume stream
    except Exception:
        pass # Ignore stream errors, we just want to log
        
    time.sleep(1) # Wait for DB write
    
    # 2. Check History
    url_history = "http://localhost:8765/api/history"
    print(f"\n🧠 Checking History at {url_history}")
    
    try:
        r = requests.get(url_history)
        if r.status_code == 200:
            data = r.json()
            history = data.get("history", [])
            print(f"✅ Found {len(history)} messages in history.")
            for msg in history[-2:]:
                print(f"   [{msg['role']}] {msg['content'][:50]}...")
        else:
            print(f"❌ Error: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_memory()
