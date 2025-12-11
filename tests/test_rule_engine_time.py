"""
Unit tests for RuleEngine time-based edge detection.

Tests the fix for the bug where get_time() and get_last_time() returned
the same value, causing time-based edge detection to fail.

Run with: pytest tests/test_rule_engine_time.py -v
"""

import sys
import pytest
from unittest.mock import MagicMock, patch


# Mock MicroPython-specific modules before importing our code
sys.modules['machine'] = MagicMock()
sys.modules['ntptime'] = MagicMock()
sys.modules['urequests'] = MagicMock()
sys.modules['ujson'] = MagicMock()


class MockTimeSync:
    """Mock TimeSync for testing."""
    
    def __init__(self):
        self.is_synced = False
        self._minute_of_day = 0
    
    def set_minute_of_day(self, minutes):
        """Set the minute of day for testing."""
        self._minute_of_day = minutes
        self.is_synced = True
    
    def get_minute_of_day(self):
        return self._minute_of_day


class MockSensorManager:
    """Mock SensorManager for testing."""
    
    def __init__(self):
        self.temperature = 25.0
        self.humidity = 50.0
        self.light_level = 2000
        self.switch_state = False
        self.reset_switch_state = False
        
        self.last_temperature = 25.0
        self.last_humidity = 50.0
        self.last_light_level = 2000
        self.last_switch_state = False
        self.last_reset_switch_state = False
        
        self._time_seconds = 0
    
    def get_temperature(self):
        return self.temperature
    
    def get_humidity(self):
        return self.humidity
    
    def get_light_level(self):
        return self.light_level
    
    def get_switch_state(self):
        return self.switch_state
    
    def get_reset_switch_state(self):
        return self.reset_switch_state
    
    def get_last_temperature(self):
        return self.last_temperature
    
    def get_last_humidity(self):
        return self.last_humidity
    
    def get_last_light_level(self):
        return self.last_light_level
    
    def get_last_switch_state(self):
        return self.last_switch_state
    
    def get_last_reset_switch_state(self):
        return self.last_reset_switch_state
    
    def get_time_seconds(self):
        return self._time_seconds
    
    def set_time_seconds(self, seconds):
        """Set time for testing."""
        self._time_seconds = seconds


class MockInstanceManager:
    """Mock InstanceManager for testing."""
    
    def __init__(self):
        self.time_sync = MockTimeSync()
        self.sensors = MockSensorManager()
        self.config = MagicMock()
        self.config.get_sensor_pins.return_value = {}


@pytest.fixture
def mock_instances():
    """Create and patch mock instances."""
    mock = MockInstanceManager()
    return mock


@pytest.fixture
def rule_engine(mock_instances):
    """Create a RuleEngine with mocked dependencies."""
    # Patch the instances module
    with patch.dict(sys.modules, {'instances': MagicMock()}):
        sys.modules['instances'].instances = mock_instances
        
        # Now import RuleEngine
        # We need to reload if already imported
        if 'rule_engine' in sys.modules:
            del sys.modules['rule_engine']
        
        # Add src to path
        import os
        src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        from rule_engine import RuleEngine
        engine = RuleEngine()
        
        yield engine, mock_instances


class TestTimeEdgeDetection:
    """Tests for time-based edge detection in rules."""
    
    def test_get_time_and_last_time_differ_after_update(self, rule_engine):
        """Verify get_time() and get_last_time() return different values after update."""
        engine, mocks = rule_engine
        
        # Set initial time to 1:00 PM (13:00)
        mocks.time_sync.set_minute_of_day(13 * 60)  # 780 minutes
        
        # First update establishes baseline
        engine.update_time()
        
        # Now advance time to 2:00 PM (14:00)
        mocks.time_sync.set_minute_of_day(14 * 60)  # 840 minutes
        
        # Update time tracking
        engine.update_time()
        
        # get_time should be 2 PM, get_last_time should be 1 PM
        current = engine.get_current_time_seconds()
        last = engine.get_last_time_seconds()
        
        assert current == 14 * 3600, f"Expected 2 PM (50400s), got {current}s"
        assert last == 13 * 3600, f"Expected 1 PM (46800s), got {last}s"
        assert current != last, "get_time and get_last_time should differ after update"
    
    def test_crossed_2pm_edge_detection(self, rule_engine):
        """Test detecting when time crosses 2 PM boundary."""
        engine, mocks = rule_engine
        
        # Set time to 1:59 PM
        mocks.time_sync.set_minute_of_day(13 * 60 + 59)  # 839 minutes = 1:59 PM
        engine.update_time()
        
        # Advance to 2:00 PM
        mocks.time_sync.set_minute_of_day(14 * 60)  # 840 minutes = 2:00 PM
        engine.update_time()
        
        # Evaluate the edge detection rule
        rule = """
last_t = get_last_time()
t = get_time()
crossed_2pm = last_t < time(14, 0) <= t
result = crossed_2pm
"""
        result = engine.evaluate(rule)
        
        assert result is True, "Should detect crossing 2 PM"
    
    def test_not_crossed_2pm_when_before(self, rule_engine):
        """Test that edge is NOT detected when still before 2 PM."""
        engine, mocks = rule_engine
        
        # Set time to 1:00 PM
        mocks.time_sync.set_minute_of_day(13 * 60)
        engine.update_time()
        
        # Advance to 1:30 PM (still before 2 PM)
        mocks.time_sync.set_minute_of_day(13 * 60 + 30)
        engine.update_time()
        
        rule = """
last_t = get_last_time()
t = get_time()
crossed_2pm = last_t < time(14, 0) <= t
result = crossed_2pm
"""
        result = engine.evaluate(rule)
        
        assert result is False, "Should NOT detect crossing 2 PM when still before"
    
    def test_not_crossed_2pm_when_already_past(self, rule_engine):
        """Test that edge is NOT detected when already past 2 PM."""
        engine, mocks = rule_engine
        
        # Set time to 2:30 PM (already past 2 PM)
        mocks.time_sync.set_minute_of_day(14 * 60 + 30)
        engine.update_time()
        
        # Advance to 3:00 PM
        mocks.time_sync.set_minute_of_day(15 * 60)
        engine.update_time()
        
        rule = """
last_t = get_last_time()
t = get_time()
crossed_2pm = last_t < time(14, 0) <= t
result = crossed_2pm
"""
        result = engine.evaluate(rule)
        
        assert result is False, "Should NOT detect crossing 2 PM when already past"
    
    def test_crossed_10pm_edge_detection(self, rule_engine):
        """Test detecting when time crosses 10 PM boundary."""
        engine, mocks = rule_engine
        
        # Set time to 9:59 PM
        mocks.time_sync.set_minute_of_day(21 * 60 + 59)  # 1319 minutes = 9:59 PM
        engine.update_time()
        
        # Advance to 10:00 PM
        mocks.time_sync.set_minute_of_day(22 * 60)  # 1320 minutes = 10:00 PM
        engine.update_time()
        
        rule = """
last_t = get_last_time()
t = get_time()
crossed_10pm = last_t < time(22, 0) <= t
result = crossed_10pm
"""
        result = engine.evaluate(rule)
        
        assert result is True, "Should detect crossing 10 PM"
    
    def test_full_user_rule_crosses_2pm(self, rule_engine):
        """Test the full user rule when crossing 2 PM (should turn OFF)."""
        engine, mocks = rule_engine
        
        # Set time to 1:59 PM, switch not pressed
        mocks.time_sync.set_minute_of_day(13 * 60 + 59)
        mocks.sensors.switch_state = False
        mocks.sensors.last_switch_state = False
        engine.update_time()
        
        # Advance to 2:00 PM
        mocks.time_sync.set_minute_of_day(14 * 60)
        engine.update_time()
        
        rule = """
switch_edge_on = get_switch_state() and not get_last_switch_state()
switch_edge_off = not get_switch_state() and get_last_switch_state()
t = get_time()
last_t = get_last_time()
crossed_2pm = last_t < time(14, 0) <= t
crossed_10pm = last_t < time(22, 0) <= t
result = False if (switch_edge_on or crossed_2pm) else (True if (switch_edge_off or crossed_10pm) else None)
"""
        result = engine.evaluate(rule)
        
        assert result is False, "Crossing 2 PM should turn lights OFF (result=False)"
    
    def test_full_user_rule_crosses_10pm(self, rule_engine):
        """Test the full user rule when crossing 10 PM (should turn ON)."""
        engine, mocks = rule_engine
        
        # Set time to 9:59 PM, switch not pressed
        mocks.time_sync.set_minute_of_day(21 * 60 + 59)
        mocks.sensors.switch_state = False
        mocks.sensors.last_switch_state = False
        engine.update_time()
        
        # Advance to 10:00 PM
        mocks.time_sync.set_minute_of_day(22 * 60)
        engine.update_time()
        
        rule = """
switch_edge_on = get_switch_state() and not get_last_switch_state()
switch_edge_off = not get_switch_state() and get_last_switch_state()
t = get_time()
last_t = get_last_time()
crossed_2pm = last_t < time(14, 0) <= t
crossed_10pm = last_t < time(22, 0) <= t
result = False if (switch_edge_on or crossed_2pm) else (True if (switch_edge_off or crossed_10pm) else None)
"""
        result = engine.evaluate(rule)
        
        assert result is True, "Crossing 10 PM should turn lights ON (result=True)"
    
    def test_full_user_rule_no_crossing(self, rule_engine):
        """Test the full user rule when no edge crossing (should return None)."""
        engine, mocks = rule_engine
        
        # Set time to 3:00 PM, switch not pressed
        mocks.time_sync.set_minute_of_day(15 * 60)
        mocks.sensors.switch_state = False
        mocks.sensors.last_switch_state = False
        engine.update_time()
        
        # Advance to 3:01 PM (no edge crossing)
        mocks.time_sync.set_minute_of_day(15 * 60 + 1)
        engine.update_time()
        
        rule = """
switch_edge_on = get_switch_state() and not get_last_switch_state()
switch_edge_off = not get_switch_state() and get_last_switch_state()
t = get_time()
last_t = get_last_time()
crossed_2pm = last_t < time(14, 0) <= t
crossed_10pm = last_t < time(22, 0) <= t
result = False if (switch_edge_on or crossed_2pm) else (True if (switch_edge_off or crossed_10pm) else None)
"""
        result = engine.evaluate(rule)
        
        assert result is None, "No edge crossing should keep state (result=None)"


class TestSwitchEdgeDetection:
    """Tests for switch-based edge detection in rules."""
    
    def test_switch_edge_on_turns_off(self, rule_engine):
        """Test that pressing switch turns lights OFF."""
        engine, mocks = rule_engine
        
        # Initial: switch not pressed
        mocks.sensors.switch_state = False
        mocks.sensors.last_switch_state = False
        mocks.time_sync.set_minute_of_day(15 * 60)  # 3 PM, no time edge
        engine.update_time()
        
        # Now: switch pressed (edge on)
        mocks.sensors.switch_state = True
        mocks.sensors.last_switch_state = False
        engine.update_time()
        
        rule = """
switch_edge_on = get_switch_state() and not get_last_switch_state()
switch_edge_off = not get_switch_state() and get_last_switch_state()
t = get_time()
last_t = get_last_time()
crossed_2pm = last_t < time(14, 0) <= t
crossed_10pm = last_t < time(22, 0) <= t
result = False if (switch_edge_on or crossed_2pm) else (True if (switch_edge_off or crossed_10pm) else None)
"""
        result = engine.evaluate(rule)
        
        assert result is False, "Switch press should turn lights OFF"
    
    def test_switch_edge_off_turns_on(self, rule_engine):
        """Test that releasing switch turns lights ON."""
        engine, mocks = rule_engine
        
        # Initial: switch pressed
        mocks.sensors.switch_state = True
        mocks.sensors.last_switch_state = True
        mocks.time_sync.set_minute_of_day(15 * 60)  # 3 PM, no time edge
        engine.update_time()
        
        # Now: switch released (edge off)
        mocks.sensors.switch_state = False
        mocks.sensors.last_switch_state = True
        engine.update_time()
        
        rule = """
switch_edge_on = get_switch_state() and not get_last_switch_state()
switch_edge_off = not get_switch_state() and get_last_switch_state()
t = get_time()
last_t = get_last_time()
crossed_2pm = last_t < time(14, 0) <= t
crossed_10pm = last_t < time(22, 0) <= t
result = False if (switch_edge_on or crossed_2pm) else (True if (switch_edge_off or crossed_10pm) else None)
"""
        result = engine.evaluate(rule)
        
        assert result is True, "Switch release should turn lights ON"


class TestTimeHelperFunction:
    """Tests for the time() helper function."""
    
    def test_time_helper_hours_only(self, rule_engine):
        """Test time() helper with hours only."""
        engine, _ = rule_engine
        
        result = engine.evaluate("time(14, 0)")
        assert result == 14 * 3600, "time(14, 0) should be 50400 seconds"
    
    def test_time_helper_hours_and_minutes(self, rule_engine):
        """Test time() helper with hours and minutes."""
        engine, _ = rule_engine
        
        result = engine.evaluate("time(14, 30)")
        assert result == 14 * 3600 + 30 * 60, "time(14, 30) should be 52200 seconds"
    
    def test_time_helper_full(self, rule_engine):
        """Test time() helper with hours, minutes, and seconds."""
        engine, _ = rule_engine
        
        result = engine.evaluate("time(14, 30, 45)")
        assert result == 14 * 3600 + 30 * 60 + 45, "time(14, 30, 45) should be 52245 seconds"


class TestTimeSyncFallback:
    """Tests for falling back to sensors when TimeSync is not available."""
    
    def test_uses_sensors_when_time_sync_not_synced(self, rule_engine):
        """Test that sensors time is used when TimeSync is not synced."""
        engine, mocks = rule_engine
        
        # TimeSync not synced
        mocks.time_sync.is_synced = False
        
        # Set sensor time to 3 PM
        mocks.sensors.set_time_seconds(15 * 3600)
        
        engine.update_time()
        
        current = engine.get_current_time_seconds()
        assert current == 15 * 3600, "Should use sensor time when TimeSync not synced"
    
    def test_uses_time_sync_when_synced(self, rule_engine):
        """Test that TimeSync is used when available and synced."""
        engine, mocks = rule_engine
        
        # TimeSync synced to 4 PM
        mocks.time_sync.set_minute_of_day(16 * 60)
        
        # Sensor time is different (3 PM)
        mocks.sensors.set_time_seconds(15 * 3600)
        
        engine.update_time()
        
        current = engine.get_current_time_seconds()
        assert current == 16 * 3600, "Should use TimeSync when synced"

