#!/usr/bin/env python3
"""
Local CodeRabbit - WebSocket Server for Real-Time Dashboard Updates
Uses a simple HTTP-based server-sent events (SSE) approach for better compatibility.
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime


# Global state
connected_clients = []
latest_update = None


class SSEHandler(BaseHTTPRequestHandler):
    """Handles Server-Sent Events connections."""
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_GET(self):
        if self.path == '/events':
            self._handle_sse()
        elif self.path == '/stats':
            self._handle_stats()
        elif self.path == '/health':
            self._handle_health()
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()
    
    def _send_cors_headers(self):
        """Add CORS headers for browser access."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def _handle_sse(self):
        """Handle Server-Sent Events stream."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self._send_cors_headers()
        self.end_headers()
        
        # Send initial connection event
        self._send_event('connected', {'time': datetime.now().isoformat()})
        
        # Add to connected clients
        connected_clients.append(self.wfile)
        
        try:
            # Keep connection alive
            while True:
                # Send heartbeat every 30 seconds
                import time
                time.sleep(30)
                self._send_event('heartbeat', {'time': datetime.now().isoformat()})
        except:
            pass
        finally:
            if self.wfile in connected_clients:
                connected_clients.remove(self.wfile)
    
    def _handle_stats(self):
        """Return current stats as JSON."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        
        stats = latest_update or {"status": "no_data"}
        self.wfile.write(json.dumps(stats).encode())
    
    def _handle_health(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        
        self.wfile.write(json.dumps({
            "status": "ok",
            "clients": len(connected_clients),
            "time": datetime.now().isoformat()
        }).encode())
    
    def _send_event(self, event_type, data):
        """Send SSE event to client."""
        try:
            message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            self.wfile.write(message.encode())
            self.wfile.flush()
        except:
            pass


def broadcast_update(data):
    """Send update to all connected clients."""
    global latest_update
    latest_update = data
    
    dead_clients = []
    for client in connected_clients:
        try:
            message = f"event: update\ndata: {json.dumps(data)}\n\n"
            client.write(message.encode())
            client.flush()
        except:
            dead_clients.append(client)
    
    # Clean up disconnected clients
    for client in dead_clients:
        connected_clients.remove(client)


def start_server(port=8765):
    """Start the SSE server in a background thread."""
    from http.server import ThreadingHTTPServer
    server = ThreadingHTTPServer(('localhost', port), SSEHandler)
    
    def run():
        print(f"[SSE] Server running on http://localhost:{port}")
        print(f"[SSE] Dashboard can connect to /events for real-time updates")
        server.serve_forever()
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return server


def notify_file_review(filepath, issues, status="reviewing"):
    """Notify clients about a file review."""
    broadcast_update({
        "type": "review",
        "file": filepath,
        "issues": {
            "critical": len(issues.get("critical", [])),
            "warning": len(issues.get("warning", [])),
            "suggestion": len(issues.get("suggestion", []))
        },
        "status": status,
        "time": datetime.now().strftime("%H:%M:%S")
    })


def notify_status(message, status="info"):
    """Send status message to clients."""
    broadcast_update({
        "type": "status",
        "message": message,
        "status": status,
        "time": datetime.now().strftime("%H:%M:%S")
    })


if __name__ == "__main__":
    import time
    
    print("Starting SSE server for testing...")
    start_server(8765)
    
    # Keep running and send test updates
    try:
        while True:
            time.sleep(5)
            notify_status("Test heartbeat", "ok")
    except KeyboardInterrupt:
        print("\nServer stopped")
