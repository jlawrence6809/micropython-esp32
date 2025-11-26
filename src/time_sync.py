# time_sync.py - NTP time synchronization for MicroPython

import ntptime
import time
from machine import RTC

class TimeSync:
    """Manages NTP time synchronization."""
    
    # NTP servers to try (in order)
    NTP_SERVERS = [
        "pool.ntp.org",
        "time.nist.gov",
        "time.windows.com"
    ]
    
    # Default timezone offset in seconds (UTC)
    # Can be overridden via set_timezone()
    TIMEZONE_OFFSET = 0
    
    def __init__(self):
        self.rtc = RTC()
        self.last_sync_time = 0
        self.is_synced = False
    
    def set_timezone(self, offset_hours):
        """Set timezone offset in hours from UTC.
        
        Examples:
            set_timezone(-8)  # PST (UTC-8)
            set_timezone(-5)  # EST (UTC-5)
            set_timezone(1)   # CET (UTC+1)
        """
        self.TIMEZONE_OFFSET = offset_hours * 3600
    
    def sync(self, retry_count=3):
        """Synchronize time with NTP server.
        
        Args:
            retry_count: Number of times to retry on failure
            
        Returns:
            True if sync successful, False otherwise
        """
        for server in self.NTP_SERVERS:
            for attempt in range(retry_count):
                try:
                    print(f"Syncing time with {server} (attempt {attempt + 1}/{retry_count})...")
                    
                    # Set NTP host
                    ntptime.host = server
                    
                    # Sync time (sets system time to UTC)
                    ntptime.settime()
                    
                    # Mark as synced
                    self.is_synced = True
                    self.last_sync_time = time.time()
                    
                    # Get current time
                    current_time = time.localtime()
                    time_str = f"{current_time[0]}-{current_time[1]:02d}-{current_time[2]:02d} {current_time[3]:02d}:{current_time[4]:02d}:{current_time[5]:02d}"
                    
                    print(f"✓ Time synced successfully: {time_str} UTC")
                    if self.TIMEZONE_OFFSET != 0:
                        offset_hours = self.TIMEZONE_OFFSET // 3600
                        print(f"  Timezone offset: UTC{offset_hours:+d}")
                    
                    return True
                    
                except Exception as e:
                    print(f"  Failed to sync with {server}: {e}")
                    if attempt < retry_count - 1:
                        time.sleep(1)  # Wait before retry
                    continue
        
        print("⚠ Failed to sync time with any NTP server")
        return False
    
    def get_time_tuple(self):
        """Get current time as tuple (year, month, day, hour, minute, second, weekday, yearday).
        
        Applies timezone offset if set.
        """
        # Get UTC time
        utc_seconds = time.time()
        
        # Apply timezone offset
        local_seconds = utc_seconds + self.TIMEZONE_OFFSET
        
        # Convert to time tuple
        return time.localtime(local_seconds)
    
    def get_hour(self):
        """Get current hour (0-23) in local timezone."""
        return self.get_time_tuple()[3]
    
    def get_minute(self):
        """Get current minute (0-59)."""
        return self.get_time_tuple()[4]
    
    def get_second(self):
        """Get current second (0-59)."""
        return self.get_time_tuple()[5]
    
    def get_minute_of_day(self):
        """Get current minute of day (0-1439).
        
        Useful for time-based automation rules.
        """
        t = self.get_time_tuple()
        return t[3] * 60 + t[4]
    
    def get_time_string(self, format_24h=True):
        """Get formatted time string.
        
        Args:
            format_24h: If True, use 24-hour format, else 12-hour with AM/PM
            
        Returns:
            Formatted time string (e.g., "14:30:45" or "2:30:45 PM")
        """
        t = self.get_time_tuple()
        hour = t[3]
        minute = t[4]
        second = t[5]
        
        if format_24h:
            return f"{hour:02d}:{minute:02d}:{second:02d}"
        else:
            # 12-hour format
            am_pm = "AM" if hour < 12 else "PM"
            hour_12 = hour % 12
            if hour_12 == 0:
                hour_12 = 12
            return f"{hour_12}:{minute:02d}:{second:02d} {am_pm}"
    
    def get_date_string(self):
        """Get formatted date string (YYYY-MM-DD)."""
        t = self.get_time_tuple()
        return f"{t[0]}-{t[1]:02d}-{t[2]:02d}"
    
    def get_datetime_string(self):
        """Get formatted date and time string."""
        return f"{self.get_date_string()} {self.get_time_string()}"
    
    def should_resync(self, interval_hours=24):
        """Check if time should be resynced.
        
        Args:
            interval_hours: Hours between syncs (default 24)
            
        Returns:
            True if resync is needed
        """
        if not self.is_synced:
            return True
        
        elapsed = time.time() - self.last_sync_time
        return elapsed > (interval_hours * 3600)
    
    def get_status(self):
        """Get sync status information.
        
        Returns:
            Dict with sync status
        """
        status = {
            "synced": self.is_synced,
            "current_time": self.get_datetime_string() if self.is_synced else "Not synced",
            "timezone_offset": f"UTC{(self.TIMEZONE_OFFSET // 3600):+d}",
        }
        
        if self.is_synced:
            elapsed = time.time() - self.last_sync_time
            hours_since_sync = elapsed // 3600
            status["hours_since_sync"] = int(hours_since_sync)
        
        return status

