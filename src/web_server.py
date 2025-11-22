import socket
import os
import uasyncio as asyncio

class WebServer:
    def __init__(self, port=80, www_dir='/www'):
        self.port = port
        self.www_dir = www_dir
        
    async def start(self):
        print(f"Starting web server on port {self.port}...")
        server = await asyncio.start_server(self.handle_client, '0.0.0.0', self.port)
        print("Web server started!")
        while True:
            await asyncio.sleep(3600)

    async def handle_client(self, reader, writer):
        try:
            request_line = await reader.readline()
            if not request_line:
                writer.close()
                await writer.wait_closed()
                return

            method, path, _ = request_line.decode().split(' ')
            
            # Read headers (consume them)
            while True:
                header = await reader.readline()
                if header == b'\r\n' or not header:
                    break
            
            if method == 'GET':
                await self.serve_file(writer, path)
            else:
                # Minimal API placeholders can go here
                writer.write(b'HTTP/1.1 405 Method Not Allowed\r\n\r\n')
                await writer.drain()
        
        except Exception as e:
            print(f"Request error: {e}")
        
        finally:
            writer.close()
            await writer.wait_closed()

    async def serve_file(self, writer, path):
        # Default to index.html for root
        if path == '/':
            path = '/index.html'
            
        # Prevent directory traversal
        if '..' in path:
            writer.write(b'HTTP/1.1 403 Forbidden\r\n\r\n')
            await writer.drain()
            return
            
        # Determine file path
        # We look for path.gz first (pre-compressed)
        gz_path = self.www_dir + path + '.gz'
        file_path = self.www_dir + path
        
        # SPA Fallback: if file doesn't exist, serve index.html
        # But we must check if the path looks like an API call or a static asset first
        try:
            os.stat(gz_path)
            serve_path = gz_path
            is_gzip = True
        except OSError:
            try:
                os.stat(file_path)
                serve_path = file_path
                is_gzip = False
            except OSError:
                # Not found - Fallback to index.html for SPA routing
                # (only if not an API call or asset with extension)
                if '.' not in path or path.endswith('.html'):
                    serve_path = self.www_dir + '/index.html.gz'
                    is_gzip = True
                else:
                    writer.write(b'HTTP/1.1 404 Not Found\r\n\r\n')
                    await writer.drain()
                    return

        # Content Type mapping
        content_type = 'text/plain'
        if path.endswith('.html'): content_type = 'text/html'
        elif path.endswith('.js'): content_type = 'application/javascript'
        elif path.endswith('.css'): content_type = 'text/css'
        elif path.endswith('.json'): content_type = 'application/json'
        elif path.endswith('.ico'): content_type = 'image/x-icon'

        try:
            with open(serve_path, 'rb') as f:
                writer.write(b'HTTP/1.1 200 OK\r\n')
                writer.write(f'Content-Type: {content_type}\r\n'.encode())
                if is_gzip:
                    writer.write(b'Content-Encoding: gzip\r\n')
                writer.write(b'Connection: close\r\n\r\n')
                await writer.drain()
                
                # Stream file in chunks
                buf = bytearray(1024)
                while True:
                    l = f.readinto(buf)
                    if not l: break
                    writer.write(buf[:l])
                    await writer.drain()
                    
        except OSError:
            writer.write(b'HTTP/1.1 500 Internal Server Error\r\n\r\n')
            await writer.drain()

