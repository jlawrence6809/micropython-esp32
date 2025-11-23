import socket
import os
import uasyncio as asyncio
import json
import machine
import gc
import time
import sys
from relays import RelayManager

class WebServer:
    def __init__(self, port=80, www_dir='/www'):
        self.port = port
        self.www_dir = www_dir
        self.start_time = time.ticks_ms()
        self.relays = RelayManager()

        
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
            print(f"Request: {method} {path}")
            
            # Read headers and look for Content-Length
            content_length = 0
            while True:
                header = await reader.readline()
                if header == b'\r\n' or not header:
                    break
                if header.lower().startswith(b'content-length:'):
                    try:
                        content_length = int(header.split(b':')[1].strip())
                    except ValueError:
                        pass
            
            # Read body if present
            body = b''
            if content_length > 0:
                print(f"Reading {content_length} bytes of body...")
                # Use read instead of readexact if readexact is not available
                body = await reader.read(content_length)
                # Ensure we got what we needed (simple check)
                if len(body) < content_length:
                     # Try one more read if incomplete (simple buffering)
                     remaining = content_length - len(body)
                     body += await reader.read(remaining)
                print(f"Body received: {body[:50]}...")
            
            # Route request
            if path.startswith('/api/'):
                await self.handle_api(writer, method, path, body)
            elif method == 'GET':
                await self.serve_file(writer, path)
            else:
                writer.write(b'HTTP/1.1 405 Method Not Allowed\r\n\r\n')
                await writer.drain()
        
        except Exception as e:
            print(f"REQUEST ERROR: {e}")
            sys.print_exception(e)
            # Try to send 500 if connection still open
            try:
                writer.write(b'HTTP/1.1 500 Internal Server Error\r\n\r\n')
                await writer.drain()
            except:
                pass
        
        finally:
            writer.close()
            await writer.wait_closed()

    async def handle_api(self, writer, method, path, body):
        print(f"Handling API: {path}")
        if path == '/api/status' and method == 'GET':
            uptime_s = time.ticks_diff(time.ticks_ms(), self.start_time) // 1000
            status = {
                'platform': 'esp32',
                'memory_free': gc.mem_free(),
                'memory_alloc': gc.mem_alloc(),
                'uptime_seconds': uptime_s,
                'frequency': machine.freq()
            }
            self._send_json(writer, status)
            await writer.drain()

        elif path == '/api/save' and method == 'POST':
            try:
                print("Decoding JSON...")
                # Expecting JSON: {"filename": "user_code.py", "code": "..."}
                # Or just raw code? Let's do JSON for flexibility
                data = json.loads(body.decode())
                filename = data.get('filename', 'user_code.py')
                code = data.get('code', '')
                
                print(f"Saving {len(code)} bytes to {filename}")
                
                # Security check on filename
                if '..' in filename or filename.startswith('/'):
                    raise ValueError("Invalid filename")
                
                # Save to src/ or root? Let's save to root for now
                with open(filename, 'w') as f:
                    f.write(code)
                
                print("File saved successfully")
                    
                self._send_json(writer, {'status': 'ok', 'message': f'Saved {filename}'})
                await writer.drain()
            except Exception as e:
                print(f"API SAVE ERROR: {e}")
                sys.print_exception(e)
                self._send_error(writer, 400, str(e))
                await writer.drain()

        elif path == '/api/restart' and method == 'POST':
            writer.write(b'HTTP/1.1 200 OK\r\n')
            writer.write(b'Content-Type: application/json\r\n\r\n')
            writer.write(b'{"status": "restarting"}')
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            
            print("Restarting via API...")
            await asyncio.sleep(0.5)
            machine.reset()

        # --- Relay Config ---
        elif path == '/api/relays/config' and method == 'GET':
            config = self.relays.get_relays()
            # Original API returned { "count": N, "relays": [...] }
            # Our get_relays returns { "relays": [...] }
            # Let's match the old shape roughly
            response_data = {
                "count": len(config.get('relays', [])),
                "relays": config.get('relays', [])
            }
            self._send_json(writer, response_data)
            await writer.drain()

        elif path == '/api/relays/config' and method == 'POST':
            try:
                data = json.loads(body.decode())
                new_relays = data.get('relays', [])
                # If full doc is passed, extract relays
                # Update config
                if self.relays.update_config(new_relays):
                    self._send_json(writer, {"success": True})
                else:
                    self._send_error(writer, 400, "Invalid config format")
                await writer.drain()
            except Exception as e:
                self._send_error(writer, 400, str(e))
                await writer.drain()

        # --- Relay Control ---
        elif path == '/api/relays/control' and method == 'POST':
            try:
                data = json.loads(body.decode())
                label = data.get('label')
                state = data.get('state')
                
                if label is None or state is None:
                    self._send_error(writer, 400, "Missing label or state")
                else:
                    if self.relays.set_relay_by_label(label, state):
                        self._send_json(writer, {"status": "success", "message": "Relay updated"})
                    else:
                        self._send_json(writer, {"status": "error", "message": "Relay not found"})
                await writer.drain()
            except Exception as e:
                self._send_error(writer, 400, str(e))
                await writer.drain()

        # --- Sensors (Dummy) ---
        elif path == '/api/sensors' and method == 'GET':
            # TODO: Implement real sensors
            sensors = {
                "Light": 500,
                "Switch": False,
                "Temperature": 25.0,
                "Humidity": 50.0
            }
            self._send_json(writer, sensors)
            await writer.drain()

        # --- Storage Info ---
        elif path == '/api/storage' and method == 'GET':
            try:
                # statvfs returns (bsize, frsize, blocks, bfree, bavail, files, ffree, favail, flag, namemax)
                stat = os.statvfs('/')
                block_size = stat[0]
                total_blocks = stat[2]
                free_blocks = stat[3]
                
                total_kb = (total_blocks * block_size) // 1024
                free_kb = (free_blocks * block_size) // 1024
                used_kb = total_kb - free_kb
                
                info = {
                    "status": "ok",
                    "spiffs_total_kb": total_kb,
                    "spiffs_used_kb": used_kb,
                    "spiffs_free_kb": free_kb,
                    "fs_type": "LittleFS" # MicroPython standard on ESP32
                }
                self._send_json(writer, info)
            except Exception as e:
                self._send_error(writer, 500, str(e))
            await writer.drain()

        else:
            writer.write(b'HTTP/1.1 404 Not Found\r\n\r\n')
            await writer.drain()

    def _send_json(self, writer, data):
        writer.write(b'HTTP/1.1 200 OK\r\n')
        writer.write(b'Content-Type: application/json\r\n')
        writer.write(b'Connection: close\r\n\r\n')
        writer.write(json.dumps(data).encode())

    def _send_error(self, writer, code, message):
        writer.write(f'HTTP/1.1 {code} Error\r\n'.encode())
        writer.write(b'Content-Type: application/json\r\n\r\n')
        writer.write(json.dumps({"error": message}).encode())

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
        elif path.endswith('.png'): content_type = 'image/png'
        elif path.endswith('.jpg'): content_type = 'image/jpeg'

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
