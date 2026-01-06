#!/usr/bin/env python3
"""
Simple development server that serves static files and proxies API requests to Flask.
This is a temporary solution for local testing. For production, use Nginx.
"""
import http.server
import socketserver
import urllib.request
import urllib.parse
from pathlib import Path
import sys

PORT = 8080
FLASK_API_URL = 'http://127.0.0.1:5000'

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/'):
            # Proxy API requests to Flask
            self.proxy_request()
        else:
            # Serve static files
            super().do_GET()
    
    def do_POST(self):
        if self.path.startswith('/api/'):
            self.proxy_request()
        else:
            super().do_POST()
    
    def do_PUT(self):
        if self.path.startswith('/api/'):
            self.proxy_request()
        else:
            super().do_PUT()
    
    def do_DELETE(self):
        if self.path.startswith('/api/'):
            self.proxy_request()
        else:
            super().do_DELETE()
    
    def do_OPTIONS(self):
        if self.path.startswith('/api/'):
            self.proxy_request()
        else:
            super().do_OPTIONS()
    
    def proxy_request(self):
        """Proxy request to Flask backend"""
        try:
            # Build URL for Flask backend
            url = f"{FLASK_API_URL}{self.path}"
            
            # Get request body if present
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            
            # Create request
            req = urllib.request.Request(url, data=body, method=self.command)
            
            # Copy headers
            for header, value in self.headers.items():
                if header.lower() not in ['host', 'connection']:
                    req.add_header(header, value)
            
            # Make request to Flask
            with urllib.request.urlopen(req) as response:
                # Get response
                data = response.read()
                
                # Send response back to client
                self.send_response(response.getcode())
                
                # Copy response headers
                for header, value in response.headers.items():
                    if header.lower() not in ['connection', 'transfer-encoding']:
                        self.send_header(header, value)
                
                # Add CORS headers
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                
                self.end_headers()
                self.wfile.write(data)
        
        except urllib.error.HTTPError as e:
            # Forward error response
            self.send_response(e.code)
            for header, value in e.headers.items():
                self.send_header(header, value)
            self.end_headers()
            self.wfile.write(e.read())
        
        except Exception as e:
            # Send error response
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_msg = {'error': str(e)}
            self.wfile.write(str(error_msg).encode())
    
    def end_headers(self):
        # Add CORS headers to all responses
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

def main():
    import os
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"🚀 Server starting...")
        print(f"📁 Serving static files from: {os.getcwd()}")
        print(f"🔗 Proxying /api/* to: {FLASK_API_URL}")
        print(f"🌐 Frontend: http://localhost:{PORT}")
        print(f"⚙️  Make sure Flask backend is running on {FLASK_API_URL}")
        print(f"\n⚠️  For production, use Nginx instead of this script!")
        print(f"\nPress Ctrl+C to stop\n")
        httpd.serve_forever()

if __name__ == "__main__":
    import os
    main()

