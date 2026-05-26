import threading
import time
import json
import requests
from realtime_server import start_server, notify_file_review, connected_clients

def test_sse_payload():
    print("🧪 Testing SSE Payload Integrity...")
    
    # 1. Start Server
    server = start_server(8766) # Use different port to avoid conflict
    time.sleep(1) # Wait for startup
    
    events = []
    
    # 2. Connect Client (Simple Thread)
    def client_thread():
        print("   headers...")
        with requests.get('http://localhost:8766/events', stream=True) as r:
            for line in r.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: "):
                        data_str = decoded[6:]
                        try:
                            events.append(json.loads(data_str))
                        except Exception:
                            pass
                    if len(events) >= 2: # Wait for connected + review
                        break

    t = threading.Thread(target=client_thread)
    t.start()
    
    # Wait for client to connect
    print("   ⏳ Waiting for client...")
    for _ in range(10):
        if len(connected_clients) > 0:
            break
        time.sleep(0.5)
        
    if len(connected_clients) == 0:
        print("❌ FAILED: Client did not register in connected_clients list")
        # Print debug info
        # exit(1) # Don't exit yet, try anyway? No, it will fail.
    
    # 3. Trigger Mock Notification
    print(f"   📢 Triggering Mock Review (Clients: {len(connected_clients)})...")
    mock_issues = {
        "critical": ["Line 1: Bad error"],
        "warning": ["Line 2: Warning"],
        "suggestion": []
    }
    
    notify_file_review("test.py", mock_issues, "complete")
    
    # 4. Wait & Verify
    t.join(timeout=5)
    
    server.shutdown()
    
    # Check assertions
    review_event = next((e for e in events if e.get("type") == "review"), None)
    
    if not review_event:
        print("❌ FAILED: No review event received")
        exit(1)
        
    print(f"   ✅ Received Event: {json.dumps(review_event, indent=2)}")
    
    if "details" not in review_event:
        print("❌ FAILED: 'details' field missing from payload")
        exit(1)
        
    if review_event["details"]["critical"][0] != "Line 1: Bad error":
        print("❌ FAILED: Critical detail mismatch")
        exit(1)
        
    print("\n✅ SUCCESS: Payload contains full details!")

if __name__ == "__main__":
    test_sse_payload()
