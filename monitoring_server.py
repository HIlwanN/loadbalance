import asyncio
import websockets
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import os
import socket
import sys
from pathlib import Path

# Store connected WebSocket clients
connected_clients = set()

def find_free_port(start_port=8000, max_port=9000):
    """Find a free port in the given range"""
    for port in range(start_port, max_port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError("No free ports found in the specified range")

async def websocket_handler(websocket, path):
    """Handle WebSocket connections"""
    print(f"New WebSocket connection established")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            print(f"Received message: {message}")
            # Broadcast message to all connected clients
            for client in connected_clients:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    connected_clients.remove(client)
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket connection closed")
        connected_clients.remove(websocket)

class MonitoringHandler(SimpleHTTPRequestHandler):
    """HTTP handler for serving the monitoring dashboard"""
    def do_GET(self):
        if self.path == '/':
            self.path = '/monitoring/index.html'
        elif self.path == '/server_ports.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'http_port': self.server.server_port,
                'ws_port': ws_port
            }).encode())
            return
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        """Handle POST requests from penetration test"""
        if self.path == '/monitoring/update':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            print(f"Received data: {data}")
            
            # Broadcast to all WebSocket clients
            asyncio.run(self.broadcast(data))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    async def broadcast(self, data):
        """Broadcast data to all connected WebSocket clients"""
        if connected_clients:
            message = json.dumps(data)
            print(f"Broadcasting to {len(connected_clients)} clients: {message}")
            await asyncio.gather(
                *[client.send(message) for client in connected_clients]
            )

async def start_websocket_server(port):
    """Start WebSocket server"""
    try:
        server = await websockets.serve(websocket_handler, 'localhost', port)
        print(f"WebSocket server started on ws://localhost:{port}")
        await server.wait_closed()
    except Exception as e:
        print(f"Error starting WebSocket server: {e}")
        sys.exit(1)

def start_http_server(port):
    """Start HTTP server"""
    try:
        server = HTTPServer(('localhost', port), MonitoringHandler)
        print(f"HTTP server started on http://localhost:{port}")
        server.serve_forever()
    except Exception as e:
        print(f"Error starting HTTP server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Change to the monitoring directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Find free ports
    http_port = find_free_port(8000, 8100)
    global ws_port
    ws_port = find_free_port(8101, 8200)
    
    print(f"Using ports - HTTP: {http_port}, WebSocket: {ws_port}")
    
    # Start HTTP server in a separate thread
    http_thread = threading.Thread(target=start_http_server, args=(http_port,))
    http_thread.daemon = True
    http_thread.start()
    
    # Start WebSocket server
    asyncio.run(start_websocket_server(ws_port)) 