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
        Get comprehensive system status as an ordered list.
        Returns a list of {"key": "...", "value": "..."} objects to guarantee order.
        """
        status_items = []
        
        # Board info
        board_name = self.board.get_name()
        status_items.append({'key': 'Board', 'value': board_name})
        status_items.append({'key': 'Chip', 'value': self.board.get_chip()})
        
        # Warn if board is unconfigured
        if board_name == "Unconfigured Board":
            status_items.append({'key': '⚠️ WARNING', 'value': "Board not configured! Set board in config.json"})
        
        status_items.append({'key': 'MicroPython', 'value': self._get_micropython_version()})
        
        # Network info
        network_info = self._get_network_info()
        for key, value in network_info:
            status_items.append({'key': key, 'value': value})
        
        # CPU info
        status_items.append({'key': 'CPU Frequency', 'value': f"{machine.freq() // 1_000_000} MHz"})
        status_items.append({'key': 'Chip Temperature', 'value': self._get_chip_temperature()})
        
        # Uptime
        status_items.append({'key': 'Uptime', 'value': self._get_uptime()})
        status_items.append({'key': 'Last Boot', 'value': self._get_boot_reason()})
        
        # Memory info
        memory_info = self._get_memory_info()
        for key, value in memory_info:
            status_items.append({'key': key, 'value': value})
        
        # Flash storage info
        flash_info = self._get_flash_info()
        for key, value in flash_info:
            status_items.append({'key': key, 'value': value})
        
        # GC info
        status_items.append({'key': 'GC Collections', 'value': str(gc.mem_alloc())})
        
        return status_items
    
    def _get_micropython_version(self):
        """Get MicroPython version string."""
        try:
            return sys.version.split()[0]
        except:
            return "Unknown"
    
    def _get_network_info(self):
        """Get WiFi network information as list of tuples."""
        info = []
        wlan = network.WLAN(network.STA_IF)
        
        # MAC address (always available)
        try:
            mac = ':'.join(['{:02X}'.format(b) for b in wlan.config('mac')])
            info.append(('MAC Address', mac))
        except:
            info.append(('MAC Address', "Unknown"))
        
        # Hostname
        hostname = self.config.get_hostname()
        info.append(('Hostname', f"{hostname}.local"))
        
        # Connection-dependent info
        if wlan.isconnected():
            try:
                ifconfig = wlan.ifconfig()
                info.append(('IP Address', ifconfig[0]))
            except:
                info.append(('IP Address', "Error"))
            
            try:
                info.append(('WiFi SSID', wlan.config('essid')))
            except:
                info.append(('WiFi SSID', "Unknown"))
            
            try:
                rssi = wlan.status('rssi')
                info.append(('WiFi Signal', f"{rssi} dBm"))
            except:
                pass  # Don't add signal if unavailable
        else:
            info.append(('IP Address', "Not connected"))
            info.append(('WiFi SSID', "Not connected"))
        
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
        """Get memory usage information as list of tuples."""
        info = []
        try:
            mem_free = gc.mem_free()
            mem_alloc = gc.mem_alloc()
            mem_total = mem_free + mem_alloc
            
            info.append(('Free Memory', f"{mem_free:,} bytes"))
            info.append(('Total Memory', f"{mem_total:,} bytes"))
            info.append(('Memory Usage', f"{(mem_alloc / mem_total * 100):.1f}%"))
        except:
            info.append(('Free Memory', "Unknown"))
            info.append(('Total Memory', "Unknown"))
            info.append(('Memory Usage', "Unknown"))
        
        return info
    
    def _get_flash_info(self):
        """Get flash storage information as list of tuples."""
        info = []
        try:
            stat = os.statvfs('/')
            block_size = stat[0]
            total_blocks = stat[2]
            free_blocks = stat[3]
            
            flash_total = (total_blocks * block_size) // 1024  # KB
            flash_free = (free_blocks * block_size) // 1024
            flash_used = flash_total - flash_free
            flash_usage_pct = (flash_used / flash_total * 100) if flash_total > 0 else 0
            
            info.append(('Flash Total', f"{flash_total:,} KB"))
            info.append(('Flash Used', f"{flash_used:,} KB"))
            info.append(('Flash Free', f"{flash_free:,} KB"))
            info.append(('Flash Usage', f"{flash_usage_pct:.1f}%"))
        except:
            info.append(('Flash Total', "Unknown"))
            info.append(('Flash Used', "Unknown"))
            info.append(('Flash Free', "Unknown"))
            info.append(('Flash Usage', "Unknown"))
        
        return info

