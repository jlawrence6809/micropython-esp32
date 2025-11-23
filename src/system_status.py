import os
import gc
import time
import machine
import network
import esp32
import sys

class SystemStatus:
    """Collects and formats system status information."""
    
    def __init__(self, board_config, start_time, config_manager):
        self.board = board_config
        self.start_time = start_time
        self.config = config_manager
    
    def get_status(self):
        """
        Get comprehensive system status as a dictionary.
        Returns a dict with human-readable key-value pairs.
        """
        status = {}
        
        # Board info
        board_name = self.board.get_name()
        status['Board'] = board_name
        status['Chip'] = self.board.get_chip()
        
        # Warn if board is unconfigured
        if board_name == "Unconfigured Board":
            status['⚠️ WARNING'] = "Board not configured! Set board in config.json"
        status['MicroPython'] = self._get_micropython_version()
        
        # Network info
        network_info = self._get_network_info()
        status.update(network_info)
        
        # CPU info
        status['CPU Frequency'] = f"{machine.freq() // 1_000_000} MHz"
        status['Chip Temperature'] = self._get_chip_temperature()
        
        # Uptime
        status['Uptime'] = self._get_uptime()
        status['Last Boot'] = self._get_boot_reason()
        
        # Memory info
        memory_info = self._get_memory_info()
        status.update(memory_info)
        
        # Flash storage info
        flash_info = self._get_flash_info()
        status.update(flash_info)
        
        # GC info
        status['GC Collections'] = str(gc.mem_alloc())
        
        return status
    
    def _get_micropython_version(self):
        """Get MicroPython version string."""
        try:
            return sys.version.split()[0]
        except:
            return "Unknown"
    
    def _get_network_info(self):
        """Get WiFi network information."""
        info = {}
        wlan = network.WLAN(network.STA_IF)
        
        # MAC address (always available)
        try:
            mac = ':'.join(['{:02X}'.format(b) for b in wlan.config('mac')])
            info['MAC Address'] = mac
        except:
            info['MAC Address'] = "Unknown"
        
        # Hostname
        hostname = self.config.get_hostname()
        info['Hostname'] = f"{hostname}.local"
        
        # Connection-dependent info
        if wlan.isconnected():
            try:
                ifconfig = wlan.ifconfig()
                info['IP Address'] = ifconfig[0]
            except:
                info['IP Address'] = "Error"
            
            try:
                info['WiFi SSID'] = wlan.config('essid')
            except:
                info['WiFi SSID'] = "Unknown"
            
            try:
                rssi = wlan.status('rssi')
                info['WiFi Signal'] = f"{rssi} dBm"
            except:
                pass  # Don't add signal if unavailable
        else:
            info['IP Address'] = "Not connected"
            info['WiFi SSID'] = "Not connected"
        
        return info
    
    def _get_chip_temperature(self):
        """Get internal chip temperature."""
        try:
            # ESP32 raw_temperature returns Fahrenheit
            temp_f = esp32.raw_temperature()
            temp_c = (temp_f - 32) * 5 / 9
            return f"{temp_c:.1f}°C ({temp_f:.1f}°F)"
        except:
            return "N/A"
    
    def _get_uptime(self):
        """Get formatted uptime string."""
        try:
            uptime_s = time.ticks_diff(time.ticks_ms(), self.start_time) // 1000
            uptime_h = uptime_s // 3600
            uptime_m = (uptime_s % 3600) // 60
            uptime_s_remaining = uptime_s % 60
            return f"{uptime_h}h {uptime_m}m {uptime_s_remaining}s"
        except:
            return "Unknown"
    
    def _get_boot_reason(self):
        """Get the reason for last boot/reset."""
        try:
            reset_cause = machine.reset_cause()
            reset_reasons = {
                machine.PWRON_RESET: "Power on",
                machine.HARD_RESET: "Hard reset",
                machine.WDT_RESET: "Watchdog",
                machine.DEEPSLEEP_RESET: "Deep sleep",
                machine.SOFT_RESET: "Software reset"
            }
            return reset_reasons.get(reset_cause, f"Unknown ({reset_cause})")
        except:
            return "Unknown"
    
    def _get_memory_info(self):
        """Get memory usage information."""
        info = {}
        try:
            mem_free = gc.mem_free()
            mem_alloc = gc.mem_alloc()
            mem_total = mem_free + mem_alloc
            
            info['Free Memory'] = f"{mem_free:,} bytes"
            info['Total Memory'] = f"{mem_total:,} bytes"
            info['Memory Usage'] = f"{(mem_alloc / mem_total * 100):.1f}%"
        except:
            info['Free Memory'] = "Unknown"
            info['Total Memory'] = "Unknown"
            info['Memory Usage'] = "Unknown"
        
        return info
    
    def _get_flash_info(self):
        """Get flash storage information."""
        info = {}
        try:
            stat = os.statvfs('/')
            block_size = stat[0]
            total_blocks = stat[2]
            free_blocks = stat[3]
            
            flash_total = (total_blocks * block_size) // 1024  # KB
            flash_free = (free_blocks * block_size) // 1024
            flash_used = flash_total - flash_free
            flash_usage_pct = (flash_used / flash_total * 100) if flash_total > 0 else 0
            
            info['Flash Total'] = f"{flash_total:,} KB"
            info['Flash Used'] = f"{flash_used:,} KB"
            info['Flash Free'] = f"{flash_free:,} KB"
            info['Flash Usage'] = f"{flash_usage_pct:.1f}%"
        except:
            info['Flash Total'] = "Unknown"
            info['Flash Used'] = "Unknown"
            info['Flash Free'] = "Unknown"
            info['Flash Usage'] = "Unknown"
        
        return info

