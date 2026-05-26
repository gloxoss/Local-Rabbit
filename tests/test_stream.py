import requests
import json
import sys

def test_stream():
    url = "http://localhost:8765/api/chat/stream"
    payload = {
        "query": "What is the watcher daemon?",
        "context": {
            "project_root": "c:/Users/zakio/Desktop/Work/Local Rabbit"
        }
    }
    
    print(f"🌊 Testing Streaming API: {url}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        with requests.post(url, json=payload, stream=True) as r:
            if r.status_code != 200:
                print(f"❌ Error: {r.status_code} - {r.text}")
                return

            print("\n🚀 Stream started...")
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data = json.loads(decoded_line[6:])
                        if data['type'] == 'token':
                            sys.stdout.write(data['content'])
                            sys.stdout.flush()
                        elif data['type'] == 'status':
                            print(f"\n[STATUS] {data['content']}")
                        elif data['type'] == 'error':
                            print(f"\n❌ Error: {data['content']}")
                        elif data['type'] == 'done':
                            print("\n✅ Stream complete.")
                            
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")

if __name__ == "__main__":
    test_stream()
