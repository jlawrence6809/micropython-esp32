import socket
import os
import uasyncio as asyncio
import json
import machine
import time
import sys
from system_status import SystemStatus

class WebServer:
    def __init__(self, port=80, www_dir='/www', config_manager=None, board_config=None, 
                 wifi_manager=None, sensor_manager=None, relay_manager=None):
        """Initialize web server with singleton instances.
        
        Args:
            port: HTTP server port (default 80)
            www_dir: Directory containing static web files
            config_manager: ConfigManager singleton instance
            board_config: BoardConfig singleton instance
            wifi_manager: WiFiManager singleton instance
            sensor_manager: SensorManager singleton instance
            relay_manager: RelayManager singleton instance
        """
        self.port = port
        self.www_dir = www_dir
        self.start_time = time.ticks_ms()
        
        # Store singleton references
        self.config = config_manager
        self.board = board_config
        self.wifi = wifi_manager
        self.sensors = sensor_manager
        self.relays = relay_manager
        
        # Initialize system status with singletons
        self.system_status = SystemStatus(self.board, self.start_time, self.config)
        
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
            status = self.system_status.get_status()
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
            relay_config = self.relays.get_relays()
            # Original API returned { "count": N, "relays": [...] }
            # Our get_relays returns { "relays": [...] }
            # Let's match the old shape roughly
            response_data = {
                "count": len(relay_config.get('relays', [])),
                "relays": relay_config.get('relays', [])
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

        # --- GPIO Options ---
        elif path == '/api/gpio/available' and method == 'GET':
            try:
                # Get pins currently in use by relays
                used_pins = [relay['pin'] for relay in self.relays.get_relays().get('relays', [])]
                
                # Get available pins from board config
                available = self.board.get_available_pins(exclude_pins=used_pins)
                
                # Return as object with pin numbers as keys (matches old API format)
                result = {str(pin): str(pin) for pin in available}
                self._send_json(writer, result)
            except Exception as e:
                self._send_error(writer, 500, str(e))
            await writer.drain()

        # --- Sensors (Dummy) ---
        elif path == '/api/sensors' and method == 'GET':
            # Return sensor data from SensorManager if available
            if self.sensors:
                sensor_data = self.sensors.to_dict()
            else:
                # Fallback to dummy data if no sensor manager
                sensor_data = {
                    "temperature": 25.0,
                    "humidity": 50.0,
                    "light_level": 500,
                    "switch_state": False,
                    "time_seconds": 0
                }
            self._send_json(writer, sensor_data)
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

        # --- WiFi Scan ---
        elif path == '/api/wifi/scan' and method == 'GET':
            try:
                networks = self.wifi.scan_networks()
                self._send_json(writer, {"networks": networks})
            except Exception as e:
                self._send_error(writer, 500, str(e))
            await writer.drain()

        # --- WiFi Connect ---
        elif path == '/api/wifi/connect' and method == 'POST':
            try:
                data = json.loads(body.decode())
                ssid = data.get('ssid')
                password = data.get('password')
                save = data.get('save', True)  # Save by default
                
                if not ssid:
                    self._send_error(writer, 400, "SSID required")
                    await writer.drain()
                    return
                
                # Try to connect
                if self.wifi.connect(ssid, password, timeout=15):
                    # Save credentials if requested
                    if save:
                        self.wifi.save_credentials(ssid, password)
                    
                    self._send_json(writer, {
                        "status": "success",
                        "message": "Connected to WiFi",
                        "ip": self.wifi.get_ip()
                    })
                else:
                    self._send_json(writer, {
                        "status": "error",
                        "message": "Failed to connect to WiFi"
                    })
            except Exception as e:
                self._send_error(writer, 500, str(e))
            await writer.drain()

        # --- WiFi Status ---
        elif path == '/api/wifi/status' and method == 'GET':
            try:
                import network
                wlan = network.WLAN(network.STA_IF)
                ap = network.WLAN(network.AP_IF)
                
                status = {
                    "sta_active": wlan.active(),
                    "sta_connected": wlan.isconnected(),
                    "ap_active": ap.active()
                }
                
                if wlan.isconnected():
                    status["sta_ip"] = wlan.ifconfig()[0]
                    status["sta_ssid"] = wlan.config('essid')
                    status["sta_rssi"] = wlan.status('rssi')
                
                if ap.active():
                    status["ap_ip"] = ap.ifconfig()[0]
                    status["ap_ssid"] = ap.config('essid')
                
                self._send_json(writer, status)
            except Exception as e:
                self._send_error(writer, 500, str(e))
            await writer.drain()

        # --- Config Get ---
        elif path == '/api/config' and method == 'GET':
            try:
                config_data = {
                    "hostname": self.config.get_hostname(),
                    "board": self.config.get_board_config_file().replace('/boards/', ''),
                    "board_name": self.board.get_name()
                }
                self._send_json(writer, config_data)
            except Exception as e:
                import sys
                sys.print_exception(e)
                self._send_error(writer, 500, str(e))
            await writer.drain()

        # --- Config Update ---
        elif path == '/api/config' and method == 'POST':
            try:
                data = json.loads(body.decode())
                hostname = data.get('hostname')
                board = data.get('board')
                
                # Validate inputs
                if hostname is not None:
                    # Basic hostname validation
                    # MicroPython doesn't have isalnum(), so check manually
                    cleaned = hostname.replace('-', '').replace('_', '')
                    if not hostname or not all(c.isalpha() or c.isdigit() for c in cleaned):
                        self._send_error(writer, 400, "Invalid hostname format")
                        await writer.drain()
                        return
                    self.config.set_hostname(hostname)
                
                if board is not None:
                    # Validate board filename - check if file exists
                    # Ensure .json extension
                    board_filename = board if board.endswith('.json') else f'{board}.json'
                    board_file = f'/boards/{board_filename}'
                    try:
                        with open(board_file, 'r') as f:
                            json.load(f)  # Validate it's valid JSON
                        self.config.set_board_config_file(board_file)
                    except (OSError, ValueError) as e:
                        self._send_error(writer, 400, f"Invalid board file: {board_filename} - {e}")
                        await writer.drain()
                        return
                
                # Save config
                if self.config.save_config():
                    self._send_json(writer, {
                        "status": "success",
                        "message": "Configuration updated. Restart required for changes to take effect.",
                        "restart_required": True
                    })
                else:
                    self._send_error(writer, 500, "Failed to save configuration")
            except Exception as e:
                import sys
                sys.print_exception(e)
                self._send_error(writer, 500, str(e))
            await writer.drain()

        # --- Available Boards ---
        elif path == '/api/boards' and method == 'GET':
            try:
                # List available board config files
                boards = []
                try:
                    files = os.listdir('/boards')
                    for filename in files:
                        if filename.endswith('.json'):
                            filepath = f'/boards/{filename}'
                            try:
                                with open(filepath, 'r') as f:
                                    board_data = json.load(f)
                                    boards.append({
                                        "filename": filename,
                                        "name": board_data.get('name', filename.replace('.json', '')),
                                        "chip": board_data.get('chip', 'Unknown'),
                                        "description": board_data.get('description', '')
                                    })
                            except:
                                pass  # Skip invalid files
                except OSError:
                    pass  # /boards directory doesn't exist
                
                self._send_json(writer, {"boards": boards})
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
