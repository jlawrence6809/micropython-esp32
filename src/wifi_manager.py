import network
import time
from instances import instances

class WiFiManager:
    """Manages WiFi connection with AP fallback."""
    
    # AP mode configuration
    AP_PASSWORD = "12345678"  # Minimum 8 characters for WPA2
    AP_CHANNEL = 11
    AP_AUTHMODE = 3  # WPA2
    
    # Connection timeouts
    CONNECT_TIMEOUT = 15  # seconds
    CONNECT_RETRY_DELAY = 1  # seconds
    
    def __init__(self):
        """Initialize WiFi manager.
        
        Uses global instances for config.
        """
        self.sta = network.WLAN(network.STA_IF)
        self.ap = network.WLAN(network.AP_IF)
        self.mode = None  # 'sta', 'ap', or None
    
    def connect(self, ssid=None, password=None, timeout=None):
        """
        Connect to WiFi network.
        
        Args:
            ssid: WiFi SSID (defaults to configured SSID)
            password: WiFi password (defaults to configured password)
            timeout: Connection timeout in seconds
        
        Returns:
            True if connected, False otherwise
        """
        if timeout is None:
            timeout = self.CONNECT_TIMEOUT
        
        if ssid is None:
            ssid = instances.config.get_wifi_ssid()
        if password is None:
            password = instances.config.get_wifi_password()
        
        print(f"Connecting to WiFi: {ssid}")
        
        # Activate station mode
        self.sta.active(True)
        
        # Disconnect if already connected
        if self.sta.isconnected():
            self.sta.disconnect()
            time.sleep(0.5)
        
        # Connect
        self.sta.connect(ssid, password)
        
        # Wait for connection
        start = time.time()
        while not self.sta.isconnected():
            if time.time() - start > timeout:
                print(f"WiFi connection timeout after {timeout}s")
                return False
            time.sleep(self.CONNECT_RETRY_DELAY)
            print(".", end="")
        
        print()
        print(f"Connected! IP: {self.sta.ifconfig()[0]}")
        self.mode = 'sta'
        
        # Disable AP mode if it was active
        if self.ap.active():
            self.ap.active(False)
        
        return True
    
    def start_ap_mode(self, ssid=None, password=None):
        """
        Start Access Point mode.
        
        Args:
            ssid: AP SSID (defaults to hostname-based name)
            password: AP password (defaults to AP_PASSWORD)
        
        Returns:
            True if AP started successfully
        """
        if ssid is None:
            # Use hostname for AP SSID
            hostname = instances.config.get_hostname()
            ssid = f"{hostname}-setup"
        if password is None:
            password = self.AP_PASSWORD
        
        print(f"Starting AP mode: {ssid}")
        
        # Deactivate station mode
        if self.sta.active():
            self.sta.active(False)
        
        # Configure and activate AP
        self.ap.active(True)
        self.ap.config(
            essid=ssid,
            password=password,
            channel=self.AP_CHANNEL,
            authmode=self.AP_AUTHMODE
        )
        
        # Wait for AP to be ready
        time.sleep(1)
        
        if self.ap.active():
            print(f"AP started! IP: {self.ap.ifconfig()[0]}")
            print(f"Connect to '{ssid}' with password '{password}'")
            self.mode = 'ap'
            return True
        else:
            print("Failed to start AP mode")
            return False
    
    def connect_with_fallback(self):
        """
        Try to connect to configured WiFi.
        If connection fails, start AP mode for configuration.
        
        Returns:
            'sta' if connected to WiFi, 'ap' if in AP mode
        """
        # Try to connect to configured WiFi
        if self.connect():
            return 'sta'
        
        # Connection failed, start AP mode
        print("WiFi connection failed, starting AP mode for setup...")
        self.start_ap_mode()
        return 'ap'
    
    def get_mode(self):
        """Get current WiFi mode."""
        return self.mode
    
    def is_connected(self):
        """Check if connected to WiFi (STA mode)."""
        return self.mode == 'sta' and self.sta.isconnected()
    
    def is_ap_mode(self):
        """Check if in AP mode."""
        return self.mode == 'ap' and self.ap.active()
    
    def get_ip(self):
        """Get current IP address."""
        if self.mode == 'sta' and self.sta.isconnected():
            return self.sta.ifconfig()[0]
        elif self.mode == 'ap' and self.ap.active():
            return self.ap.ifconfig()[0]
        return None
    
    def scan_networks(self):
        """
        Scan for available WiFi networks.
        
        Returns:
            List of tuples: (ssid, bssid, channel, RSSI, authmode, hidden)
        """
        if not self.sta.active():
            self.sta.active(True)
            time.sleep(0.5)
        
        print("Scanning for WiFi networks...")
        networks = self.sta.scan()
        
        # Convert to more readable format
        result = []
        for net in networks:
            ssid = net[0].decode('utf-8')
            rssi = net[3]
            authmode = net[4]
            result.append({
                'ssid': ssid,
                'rssi': rssi,
                'authmode': authmode,
                'security': self._authmode_to_string(authmode)
            })
        
        # Sort by signal strength
        result.sort(key=lambda x: x['rssi'], reverse=True)
        return result
    
    def _authmode_to_string(self, authmode):
        """Convert authmode number to string."""
        modes = {
            0: 'Open',
            1: 'WEP',
            2: 'WPA-PSK',
            3: 'WPA2-PSK',
            4: 'WPA/WPA2-PSK'
        }
        return modes.get(authmode, 'Unknown')
    
    def save_credentials(self, ssid, password):
        """
        Save WiFi credentials to config.json file.
        
        Args:
            ssid: WiFi SSID
            password: WiFi password
        
        Returns:
            True if saved successfully
        """
        try:
            instances.config.set_wifi_credentials(ssid, password)
            instances.config.save_config()
            print(f"WiFi credentials saved: {ssid}")
            return True
        except Exception as e:
            print(f"Failed to save credentials: {e}")
            return False
    
    def set_hostname(self, hostname=None):
        """Set device hostname.
        
        Args:
            hostname: Hostname to set (defaults to config hostname)
        
        Returns:
            True if successful, False otherwise
        """
        if hostname is None:
            hostname = instances.config.get_hostname()
        
        try:
            network.hostname(hostname)
            print(f'Hostname set to: {hostname}')
            return True
        except Exception as e:
            print(f'Failed to set hostname: {e}')
            return False
    
    def setup_mdns(self, hostname=None):
        """Setup mDNS responder for hostname.local access.
        
        Args:
            hostname: Hostname for mDNS (defaults to config hostname)
        
        Returns:
            mDNS server instance or None if failed/unavailable
        """
        if hostname is None:
            hostname = instances.config.get_hostname()
        
        try:
            import mdns
            mdns_server = mdns.Server()
            mdns_server.start(hostname, "MicroPython ESP32 Automation")
            print(f"mDNS started: {hostname}.local")
            return mdns_server
        except ImportError:
            print("mDNS not available (requires esp32 port with mdns module)")
            return None
        except Exception as e:
            print(f"Failed to start mDNS: {e}")
            return None
    
    def setup_and_connect(self):
        """Complete WiFi setup flow with hostname, connection, and mDNS.
        
        This method handles the complete WiFi initialization sequence:
        1. Check if credentials are configured
        2. Set hostname
        3. Connect to WiFi (or start AP mode as fallback)
        4. Setup mDNS if in station mode
        
        Returns:
            tuple: (mode, mdns_server) where:
                - mode: 'sta' if connected to WiFi, 'ap' if in AP mode
                - mdns_server: mDNS server instance (if in STA mode), None otherwise
        """
        hostname = instances.config.get_hostname()
        # Set hostname before connecting
        self.set_hostname(hostname)
        
        # Check if WiFi credentials are configured
        if not instances.config.get_wifi_ssid() or not instances.config.get_wifi_password():
            print('WiFi credentials not configured, starting AP mode...')
            self.start_ap_mode()
            print(f"Connect to '{hostname}-setup' network to configure WiFi")
            mode = 'ap'
        else:
            # Try to connect with AP fallback
            mode = self.connect_with_fallback()
        
        # Setup mDNS (works in both STA and AP mode)
        mdns_server = self.setup_mdns(hostname)
        
        return mode, mdns_server

