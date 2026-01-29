import http.server
import socketserver
import json
import os
from pathlib import Path

# Configuration
PORT = 8080
ROOT_DIR = Path(__file__).parent.parent

class CodeRabbitHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        """Handle POST requests for saving files."""
        if self.path == '/api/save-prompt':
            try:
                # Read content length
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length == 0:
                    raise ValueError("Empty body")

                # Read body
                body = self.rfile.read(content_length)
                data = json.loads(body)

                # Validate structure (basic check)
                if 'review_prompt' not in data:
                    raise ValueError("Missing 'review_prompt'")

                # Save to prompts.json
                prompts_path = ROOT_DIR / 'prompts.json'
                with open(prompts_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                
                print(f"✅ Saved prompts.json via API")

                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status":"success", "message": "Saved successfully"}')

            except Exception as e:
                print(f"❌ Error saving prompt: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"status": "error", "message": str(e)}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_error(404, "Endpoint not found")

    def do_OPTIONS(self):
        """Handle preflight requests for CORS."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == "__main__":
    # Change to root dir so files are served correctly
    os.chdir(ROOT_DIR)
    
    # Use ThreadingTCPServer for concurrent requests
    class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        pass

    with ThreadingSimpleServer(("", PORT), CodeRabbitHandler) as httpd:
        print(f"🚀 Dashboard Server running at http://localhost:{PORT}")
        print(f"📂 Serving: {ROOT_DIR}")
        print("⚡ API: POST /api/save-prompt enabled")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.server_close()
