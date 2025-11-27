import socket
import os
import uasyncio as asyncio
import json
import machine
import time
import sys
from system_status import SystemStatus
from instances import instances

class WebServer:
    def __init__(self, port=80, www_dir='/www'):
        """Initialize web server.
        
        Args:
            port: HTTP server port (default 80)
            www_dir: Directory containing static web files
        """
        self.port = port
        self.www_dir = www_dir
        self.start_time = time.ticks_ms()
        
        # Initialize system status
        self.system_status = SystemStatus(self.start_time)
        
        # API route registry: (method, path) -> handler function
        self.routes = {
            ('GET', '/api/status'): self.api_status_get,
            ('POST', '/api/save'): self.api_save_post,
            ('POST', '/api/restart'): self.api_restart_post,
            ('GET', '/api/relays/config'): self.api_relays_config_get,
            ('POST', '/api/relays/config'): self.api_relays_config_post,
            ('POST', '/api/relays/control'): self.api_relays_control_post,
            ('GET', '/api/gpio/available'): self.api_gpio_available_get,
            ('GET', '/api/sensors'): self.api_sensors_get,
            ('POST', '/api/validate-rule'): self.api_validate_rule_post,
            ('GET', '/api/storage'): self.api_storage_get,
            ('GET', '/api/wifi/scan'): self.api_wifi_scan_get,
            ('POST', '/api/wifi/connect'): self.api_wifi_connect_post,
            ('GET', '/api/wifi/status'): self.api_wifi_status_get,
            ('GET', '/api/config'): self.api_config_get,
            ('POST', '/api/config'): self.api_config_post,
            ('GET', '/api/boards'): self.api_boards_get,
        }
        
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
                body = await reader.read(content_length)
                if len(body) < content_length:
                    remaining = content_length - len(body)
                    body += await reader.read(remaining)
                print(f"Body received: {body[:50]}...")
            
            # Route request
            if path.startswith('/api/'):
                await self.handle_api(writer, method, path, body)
            elif method == 'GET':
                await self.serve_file(writer, path)
            else:
                await self._send_response(writer, 405, 'Method Not Allowed')
        
        except Exception as e:
            # Don't log ECONNABORTED - client disconnected, which is normal
            if "ECONNABORTED" not in str(e):
                print(f"REQUEST ERROR: {e}")
                sys.print_exception(e)
            
            # Try to send 500 if connection still open
            try:
                await self._send_response(writer, 500, {'error': 'Internal server error'})
            except:
                pass  # Connection already closed
        
        finally:
            writer.close()
            await writer.wait_closed()

    async def handle_api(self, writer, method, path, body):
        """Route API requests to appropriate handlers with unified error handling."""
        print(f"API: {method} {path}")
        
        # Look up handler
        handler = self.routes.get((method, path))
        
        if not handler:
            await self._send_response(writer, 404, {'error': 'Not found'})
            return
        
        try:
            # Call handler - returns response data or None if handler sent response
            result = await handler(writer, body)
            
            if result is None:
                # Handler already sent response (e.g., restart endpoint)
                return
            
            # Send success response
            await self._send_response(writer, 200, result)
            
        except ValueError as e:
            # Client error (bad request)
            await self._send_response(writer, 400, {'error': str(e)})
        except Exception as e:
            # Server error
            print(f"API ERROR ({method} {path}): {e}")
            sys.print_exception(e)
            await self._send_response(writer, 500, {'error': 'Internal server error'})

    # ============================================================================
    # Helper Methods
    # ============================================================================
    
    async def _send_response(self, writer, status_code, data):
        """Send HTTP response with safe drain handling."""
        try:
            # Status text mapping
            status_text = {
                200: 'OK',
                400: 'Bad Request',
                404: 'Not Found',
                405: 'Method Not Allowed',
                500: 'Internal Server Error'
            }.get(status_code, 'Unknown')
            
            # Write status line
            writer.write(f'HTTP/1.1 {status_code} {status_text}\r\n'.encode())
            
            # Write response body
            if isinstance(data, (dict, list)):
                writer.write(b'Content-Type: application/json\r\n')
                writer.write(b'Connection: close\r\n\r\n')
                writer.write(json.dumps(data).encode())
            else:
                writer.write(b'Content-Type: text/plain\r\n')
                writer.write(b'Connection: close\r\n\r\n')
                writer.write(str(data).encode())
            
            # Safe drain - ignore ECONNABORTED
            await self._safe_drain(writer)
            
        except Exception as e:
            # Connection error during send - log if not ECONNABORTED
            if "ECONNABORTED" not in str(e):
                print(f"Response send error: {e}")

    async def _safe_drain(self, writer):
        """Drain writer, silently handling connection aborts."""
        try:
            await writer.drain()
        except OSError as e:
            if e.errno != 113:  # Not ECONNABORTED
                raise  # Re-raise other OS errors
            # Otherwise silently ignore - client disconnected

    # ============================================================================
    # API Handlers - System
    # ============================================================================

    async def api_status_get(self, writer, body):
        """GET /api/status - Get system status."""
        status = self.system_status.get_status()
        return status

    async def api_save_post(self, writer, body):
        """POST /api/save - Save a file to filesystem."""
        data = json.loads(body.decode())
        filename = data.get('filename', 'user_code.py')
        code = data.get('code', '')
        
        print(f"Saving {len(code)} bytes to {filename}")
        
        # Security check
        if '..' in filename or filename.startswith('/'):
            raise ValueError("Invalid filename")
        
        with open(filename, 'w') as f:
            f.write(code)
        
        print("File saved successfully")
        return {'status': 'ok', 'message': f'Saved {filename}'}

    async def api_restart_post(self, writer, body):
        """POST /api/restart - Restart the device."""
        # Send response immediately
        writer.write(b'HTTP/1.1 200 OK\r\n')
        writer.write(b'Content-Type: application/json\r\n\r\n')
        writer.write(b'{"status": "restarting"}')
        await self._safe_drain(writer)
        writer.close()
        await writer.wait_closed()
        
        print("Restarting via API...")
        await asyncio.sleep(0.5)
        machine.reset()
        
        return None  # Response already sent

    # ============================================================================
    # API Handlers - Relays
    # ============================================================================

    async def api_relays_config_get(self, writer, body):
        """GET /api/relays/config - Get relay configuration."""
        relay_config = instances.relays.get_relays()
        return {
            "count": len(relay_config.get('relays', [])),
            "relays": relay_config.get('relays', [])
        }

    async def api_relays_config_post(self, writer, body):
        """POST /api/relays/config - Update relay configuration."""
        data = json.loads(body.decode())
        new_relays = data.get('relays', [])
        
        if instances.relays.update_config(new_relays):
            return {"success": True}
        else:
            raise ValueError("Invalid config format")

    async def api_relays_control_post(self, writer, body):
        """POST /api/relays/control - Control a relay."""
        data = json.loads(body.decode())
        label = data.get('label')
        state = data.get('state')
        
        if label is None or state is None:
            raise ValueError("Missing label or state")
        
        if instances.relays.set_relay_by_label(label, state):
            return {"status": "success", "message": "Relay updated"}
        else:
            return {"status": "error", "message": "Relay not found"}

    # ============================================================================
    # API Handlers - GPIO & Sensors
    # ============================================================================

    async def api_gpio_available_get(self, writer, body):
        """GET /api/gpio/available - Get available GPIO pins."""
        # Get pins currently in use
        used_pins = [relay['pin'] for relay in instances.relays.get_relays().get('relays', [])]
        
        # Get available pins from board config
        available = instances.board.get_available_pins(exclude_pins=used_pins)
        
        # Return as object with pin numbers as keys
        return {str(pin): str(pin) for pin in available}

    async def api_sensors_get(self, writer, body):
        """GET /api/sensors - Get sensor data."""
        if instances.sensors:
            return instances.sensors.to_dict()
        else:
            # Fallback to dummy data
            return {
                "temperature": 25.0,
                "humidity": 50.0,
                "light_level": 500,
                "switch_state": False,
                "time_seconds": 0
            }

    async def api_validate_rule_post(self, writer, body):
        """POST /api/validate-rule - Validate a rule expression."""
        # Get rule code (strip quotes if present)
        rule_code = body.decode('utf-8').strip()
        if rule_code.startswith('"') and rule_code.endswith('"'):
            rule_code = rule_code[1:-1]
        
        # Step 1: Validate syntax
        valid, error = instances.rules.validate(rule_code)
        
        if not valid:
            return {'success': False, 'error': error}
        
        # Step 2: Test-execute with current sensor values
        try:
            result = instances.rules.evaluate(rule_code)
            return {
                'success': True,
                'message': f'Rule is valid and evaluates to: {result}'
            }
        except Exception as e:
            # Catch runtime errors
            return {
                'success': False,
                'error': f'Runtime error: {str(e)}'
            }

    # ============================================================================
    # API Handlers - Storage
    # ============================================================================

    async def api_storage_get(self, writer, body):
        """GET /api/storage - Get storage information."""
        stat = os.statvfs('/')
        block_size = stat[0]
        total_blocks = stat[2]
        free_blocks = stat[3]
        
        total_kb = (total_blocks * block_size) // 1024
        free_kb = (free_blocks * block_size) // 1024
        used_kb = total_kb - free_kb
        
        return {
            "status": "ok",
            "spiffs_total_kb": total_kb,
            "spiffs_used_kb": used_kb,
            "spiffs_free_kb": free_kb,
            "fs_type": "LittleFS"
        }

    # ============================================================================
    # API Handlers - WiFi
    # ============================================================================

    async def api_wifi_scan_get(self, writer, body):
        """GET /api/wifi/scan - Scan for WiFi networks."""
        networks = instances.wifi.scan_networks()
        return {"networks": networks}

    async def api_wifi_connect_post(self, writer, body):
        """POST /api/wifi/connect - Connect to WiFi network."""
        data = json.loads(body.decode())
        ssid = data.get('ssid')
        password = data.get('password')
        save = data.get('save', True)
        
        if not ssid:
            raise ValueError("SSID required")
        
        # Try to connect
        if instances.wifi.connect(ssid, password, timeout=15):
            # Save credentials if requested
            if save:
                instances.wifi.save_credentials(ssid, password)
            
            return {
                "status": "success",
                "message": "Connected to WiFi",
                "ip": instances.wifi.get_ip()
            }
        else:
            return {
                "status": "error",
                "message": "Failed to connect to WiFi"
            }

    async def api_wifi_status_get(self, writer, body):
        """GET /api/wifi/status - Get WiFi connection status."""
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
        
        return status

    # ============================================================================
    # API Handlers - Config
    # ============================================================================

    async def api_config_get(self, writer, body):
        """GET /api/config - Get system configuration."""
        return {
            "hostname": instances.config.get_hostname(),
            "board": instances.config.get_board_config_file().replace('/boards/', ''),
            "board_name": instances.board.get_name()
        }

    async def api_config_post(self, writer, body):
        """POST /api/config - Update system configuration."""
        data = json.loads(body.decode())
        hostname = data.get('hostname')
        board = data.get('board')
        
        # Validate and update hostname
        if hostname is not None:
            cleaned = hostname.replace('-', '').replace('_', '')
            if not hostname or not all(c.isalpha() or c.isdigit() for c in cleaned):
                raise ValueError("Invalid hostname format")
            instances.config.set_hostname(hostname)
        
        # Validate and update board
        if board is not None:
            board_filename = board if board.endswith('.json') else f'{board}.json'
            board_file = f'/boards/{board_filename}'
            try:
                with open(board_file, 'r') as f:
                    json.load(f)  # Validate it's valid JSON
                instances.config.set_board_config_file(board_file)
            except (OSError, ValueError) as e:
                raise ValueError(f"Invalid board file: {board_filename} - {e}")
        
        # Save config
        if instances.config.save_config():
            return {
                "status": "success",
                "message": "Configuration updated. Restart required for changes to take effect.",
                "restart_required": True
            }
        else:
            raise Exception("Failed to save configuration")

    async def api_boards_get(self, writer, body):
        """GET /api/boards - Get list of available boards."""
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
        
        return {"boards": boards}

    # ============================================================================
    # Static File Serving
    # ============================================================================

    async def serve_file(self, writer, path):
        """Serve static files with SPA fallback."""
        # Default to index.html for root
        if path == '/':
            path = '/index.html'
            
        # Prevent directory traversal
        if '..' in path:
            await self._send_response(writer, 403, 'Forbidden')
            return
            
        # Try to find file (check .gz first)
        gz_path = self.www_dir + path + '.gz'
        file_path = self.www_dir + path
        
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
                # SPA Fallback: serve index.html for routes
                if '.' not in path or path.endswith('.html'):
                    serve_path = self.www_dir + '/index.html.gz'
                    is_gzip = True
                else:
                    await self._send_response(writer, 404, 'Not Found')
                    return

        # Determine content type
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
                await self._safe_drain(writer)
                
                # Stream file in chunks
                buf = bytearray(1024)
                while True:
                    l = f.readinto(buf)
                    if not l: break
                    writer.write(buf[:l])
                    await self._safe_drain(writer)
                    
        except OSError:
            await self._send_response(writer, 500, 'Internal Server Error')
