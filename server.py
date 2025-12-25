#!/usr/bin/env python3
"""
Simple HTTP server to serve the web application locally
"""
import http.server
import socketserver
import os
import webbrowser
import sys
import socket
from pathlib import Path

DEFAULT_PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow loading JSON
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def log_message(self, format, *args):
        # Custom log format
        print(f"[{self.log_date_time_string()}] {format % args}")

def find_free_port(start_port):
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return None

def main():
    # Parse command line arguments for port
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"⚠️  Invalid port number: {sys.argv[1]}. Using default port {DEFAULT_PORT}")
            port = DEFAULT_PORT
    
    # Change to the script's directory
    os.chdir(Path(__file__).parent)
    
    Handler = MyHTTPRequestHandler
    
    # Try to bind to the requested port, or find a free one
    actual_port = find_free_port(port)
    if actual_port is None:
        print(f"❌ Error: Could not find an available port starting from {port}")
        print("💡 Try closing other applications using ports 8000-8099")
        sys.exit(1)
    
    if actual_port != port:
        print(f"⚠️  Port {port} is already in use. Using port {actual_port} instead.")
    
    try:
        with socketserver.TCPServer(("", actual_port), Handler) as httpd:
            print(f"🚀 Server started at http://localhost:{actual_port}")
            print(f"📁 Serving directory: {os.getcwd()}")
            print(f"🌐 Open http://localhost:{actual_port} in your browser")
            print("Press Ctrl+C to stop the server\n")
            
            # Try to open browser automatically
            try:
                webbrowser.open(f'http://localhost:{actual_port}')
            except:
                pass
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n\n👋 Server stopped")
    except OSError as e:
        print(f"❌ Error starting server: {e}")
        if e.errno == 48:  # Address already in use
            print(f"💡 Port {actual_port} is already in use.")
            print(f"💡 Try: python3 server.py {actual_port + 1}")
        sys.exit(1)

if __name__ == "__main__":
    main()

