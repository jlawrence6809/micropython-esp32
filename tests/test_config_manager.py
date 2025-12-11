"""
Unit tests for ConfigManager - configuration loading, saving, getters/setters.

Run with: pytest tests/test_config_manager.py -v
"""

import sys
import json
import pytest
from unittest.mock import MagicMock, patch, mock_open


@pytest.fixture
def config_manager():
    """Create a ConfigManager with mocked file operations."""
    import os
    src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    if 'config_manager' in sys.modules:
        del sys.modules['config_manager']
    
    # Start with empty/default config
    with patch('builtins.open', mock_open(read_data='{}')):
        from config_manager import ConfigManager
        manager = ConfigManager()
        
        yield manager


@pytest.fixture
def config_manager_with_data():
    """Create a ConfigManager with pre-populated data."""
    import os
    src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    if 'config_manager' in sys.modules:
        del sys.modules['config_manager']
    
    config_data = {
        "wifi": {
            "ssid": "TestNetwork",
            "password": "TestPassword123"
        },
        "hostname": "test-esp32",
        "board": "esp32s3_devkitc.json",
        "timezone": {
            "name": "America/Los_Angeles",
            "offset_seconds": -28800
        },
        "sensor_pins": {
            "i2c_scl": 1,
            "i2c_sda": 2,
            "ds18b20": 38,
            "photo_sensor": 4,
            "light_switch": 5,
            "reset_switch": 6
        },
        "last_known_time": 1700000000
    }
    
    with patch('builtins.open', mock_open(read_data=json.dumps(config_data))):
        from config_manager import ConfigManager
        manager = ConfigManager()
        
        yield manager


class TestConfigManagerInit:
    """Tests for ConfigManager initialization."""
    
    def test_init_with_empty_file(self, config_manager):
        """Should load empty dict when config file contains empty JSON."""
        manager = config_manager
        
        # When file contains {}, it loads that empty dict
        # Defaults are only used when file is missing or invalid
        assert manager.data is not None
        assert manager.data == {}
    
    def test_init_with_missing_file(self):
        """Should use defaults when config file doesn't exist."""
        import os
        src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        if 'config_manager' in sys.modules:
            del sys.modules['config_manager']
        
        with patch('builtins.open', side_effect=OSError("File not found")):
            from config_manager import ConfigManager
            manager = ConfigManager()
        
        assert manager.data is not None
        assert manager.get_hostname() == 'esp32'  # Default
    
    def test_init_with_valid_config(self, config_manager_with_data):
        """Should load data from valid config file."""
        manager = config_manager_with_data
        
        assert manager.get_wifi_ssid() == "TestNetwork"
        assert manager.get_hostname() == "test-esp32"


class TestWifiMethods:
    """Tests for WiFi configuration methods."""
    
    def test_get_wifi_ssid(self, config_manager_with_data):
        """Should return configured WiFi SSID."""
        manager = config_manager_with_data
        
        assert manager.get_wifi_ssid() == "TestNetwork"
    
    def test_get_wifi_ssid_not_configured(self, config_manager):
        """Should return None when WiFi not configured."""
        manager = config_manager
        
        assert manager.get_wifi_ssid() is None
    
    def test_get_wifi_password(self, config_manager_with_data):
        """Should return configured WiFi password."""
        manager = config_manager_with_data
        
        assert manager.get_wifi_password() == "TestPassword123"
    
    def test_get_wifi_password_not_configured(self, config_manager):
        """Should return None when WiFi not configured."""
        manager = config_manager
        
        assert manager.get_wifi_password() is None
    
    def test_set_wifi_credentials(self, config_manager):
        """Should set WiFi credentials."""
        manager = config_manager
        
        manager.set_wifi_credentials("NewSSID", "NewPassword")
        
        assert manager.get_wifi_ssid() == "NewSSID"
        assert manager.get_wifi_password() == "NewPassword"
    
    def test_set_wifi_creates_wifi_dict(self, config_manager):
        """Should create wifi dict if it doesn't exist."""
        manager = config_manager
        manager.data = {}
        
        manager.set_wifi_credentials("SSID", "Pass")
        
        assert 'wifi' in manager.data
        assert manager.data['wifi']['ssid'] == "SSID"


class TestHostnameMethods:
    """Tests for hostname methods."""
    
    def test_get_hostname(self, config_manager_with_data):
        """Should return configured hostname."""
        manager = config_manager_with_data
        
        assert manager.get_hostname() == "test-esp32"
    
    def test_get_hostname_default(self, config_manager):
        """Should return default hostname when not configured."""
        manager = config_manager
        manager.data = {}
        
        assert manager.get_hostname() == "esp32"
    
    def test_set_hostname(self, config_manager):
        """Should set hostname."""
        manager = config_manager
        
        manager.set_hostname("my-custom-esp")
        
        assert manager.get_hostname() == "my-custom-esp"


class TestBoardMethods:
    """Tests for board configuration methods."""
    
    def test_get_board_filename(self, config_manager_with_data):
        """Should return board filename."""
        manager = config_manager_with_data
        
        assert manager.get_board_filename() == "esp32s3_devkitc.json"
    
    def test_get_board_filename_default(self, config_manager):
        """Should return default board filename."""
        manager = config_manager
        manager.data = {}
        
        assert manager.get_board_filename() == "unconfigured.json"
    
    def test_get_board_filename_adds_json_extension(self, config_manager):
        """Should add .json extension if missing."""
        manager = config_manager
        manager.data = {'board': 'myboard'}
        
        assert manager.get_board_filename() == "myboard.json"
    
    def test_get_board_config_file(self, config_manager_with_data):
        """Should return full board config file path."""
        manager = config_manager_with_data
        
        assert manager.get_board_config_file() == "/boards/esp32s3_devkitc.json"
    
    def test_set_board_config_file_with_path(self, config_manager):
        """Should extract filename from full path."""
        manager = config_manager
        
        manager.set_board_config_file("/boards/esp32c6_devkit.json")
        
        assert manager.get_board_filename() == "esp32c6_devkit.json"
    
    def test_set_board_config_file_just_filename(self, config_manager):
        """Should accept just filename."""
        manager = config_manager
        
        manager.set_board_config_file("esp32c6_devkit.json")
        
        assert manager.get_board_filename() == "esp32c6_devkit.json"
    
    def test_set_board_config_file_adds_extension(self, config_manager):
        """Should add .json extension if missing."""
        manager = config_manager
        
        manager.set_board_config_file("esp32c6_devkit")
        
        assert manager.get_board_filename() == "esp32c6_devkit.json"
    
    def test_legacy_board_config_migration(self, config_manager):
        """Should migrate legacy board_config to board."""
        manager = config_manager
        manager.data = {
            'board_config': '/boards/old_board.json'
        }
        
        # Mock save_config to prevent actual file write
        with patch.object(manager, 'save_config', return_value=True):
            result = manager.get_board_filename()
        
        assert result == "old_board.json"
        assert 'board' in manager.data
        assert 'board_config' not in manager.data


class TestTimezoneMethods:
    """Tests for timezone methods."""
    
    def test_get_timezone_offset_seconds(self, config_manager_with_data):
        """Should return timezone offset in seconds."""
        manager = config_manager_with_data
        
        # -8 hours = -28800 seconds
        assert manager.get_timezone_offset_seconds() == -28800
    
    def test_get_timezone_offset_default(self, config_manager):
        """Should return 0 when not configured (UTC)."""
        manager = config_manager
        manager.data = {}
        
        assert manager.get_timezone_offset_seconds() == 0
    
    def test_get_timezone_name(self, config_manager_with_data):
        """Should return timezone name."""
        manager = config_manager_with_data
        
        assert manager.get_timezone_name() == "America/Los_Angeles"
    
    def test_get_timezone_name_default(self, config_manager):
        """Should return UTC when not configured."""
        manager = config_manager
        manager.data = {}
        
        assert manager.get_timezone_name() == "UTC"
    
    def test_set_timezone(self, config_manager):
        """Should set timezone configuration."""
        manager = config_manager
        
        manager.set_timezone("America/New_York", -18000)  # -5 hours
        
        assert manager.get_timezone_name() == "America/New_York"
        assert manager.get_timezone_offset_seconds() == -18000


class TestLastKnownTimeMethods:
    """Tests for last known time methods."""
    
    def test_get_last_known_time(self, config_manager_with_data):
        """Should return last known time."""
        manager = config_manager_with_data
        
        assert manager.get_last_known_time() == 1700000000
    
    def test_get_last_known_time_not_set(self, config_manager):
        """Should return None when not set."""
        manager = config_manager
        manager.data = {}
        
        assert manager.get_last_known_time() is None
    
    def test_set_last_known_time(self, config_manager):
        """Should set last known time."""
        manager = config_manager
        
        manager.set_last_known_time(1700000001)
        
        assert manager.get_last_known_time() == 1700000001


class TestSensorPinMethods:
    """Tests for sensor pin configuration methods."""
    
    def test_get_sensor_pins(self, config_manager_with_data):
        """Should return all sensor pins."""
        manager = config_manager_with_data
        
        pins = manager.get_sensor_pins()
        
        assert pins['i2c_scl'] == 1
        assert pins['i2c_sda'] == 2
        assert pins['ds18b20'] == 38
        assert pins['photo_sensor'] == 4
        assert pins['light_switch'] == 5
        assert pins['reset_switch'] == 6
    
    def test_get_sensor_pins_defaults(self, config_manager):
        """Should return defaults for missing pins."""
        manager = config_manager
        manager.data = {}
        
        pins = manager.get_sensor_pins()
        
        assert pins['i2c_scl'] == -1
        assert pins['i2c_sda'] == -1
        assert pins['ds18b20'] == -1
        assert pins['photo_sensor'] == -1
        assert pins['light_switch'] == -1
        assert pins['reset_switch'] == -1
    
    def test_get_sensor_pins_partial(self, config_manager):
        """Should return defaults for missing pins, configured for others."""
        manager = config_manager
        manager.data = {
            'sensor_pins': {
                'i2c_scl': 10,
                'i2c_sda': 11
            }
        }
        
        pins = manager.get_sensor_pins()
        
        assert pins['i2c_scl'] == 10
        assert pins['i2c_sda'] == 11
        assert pins['ds18b20'] == -1  # Default
    
    def test_get_sensor_pin(self, config_manager_with_data):
        """Should return specific sensor pin."""
        manager = config_manager_with_data
        
        assert manager.get_sensor_pin('i2c_scl') == 1
        assert manager.get_sensor_pin('ds18b20') == 38
    
    def test_get_sensor_pin_unknown_key(self, config_manager):
        """Should return -1 for unknown key."""
        manager = config_manager
        
        assert manager.get_sensor_pin('unknown_sensor') == -1
    
    def test_set_sensor_pins(self, config_manager):
        """Should set sensor pins."""
        manager = config_manager
        
        result = manager.set_sensor_pins({
            'i2c_scl': 21,
            'i2c_sda': 22
        })
        
        assert result is True
        assert manager.get_sensor_pin('i2c_scl') == 21
        assert manager.get_sensor_pin('i2c_sda') == 22
    
    def test_set_sensor_pins_merges(self, config_manager):
        """Should merge with existing pins, not replace all."""
        manager = config_manager
        manager.data = {
            'sensor_pins': {
                'i2c_scl': 1,
                'i2c_sda': 2,
                'ds18b20': 38
            }
        }
        
        manager.set_sensor_pins({
            'photo_sensor': 4
        })
        
        # Original pins should still be there
        assert manager.get_sensor_pin('i2c_scl') == 1
        assert manager.get_sensor_pin('ds18b20') == 38
        # New pin should be added
        assert manager.get_sensor_pin('photo_sensor') == 4
    
    def test_set_sensor_pins_invalid_key(self, config_manager):
        """Should reject unknown pin keys."""
        manager = config_manager
        
        result = manager.set_sensor_pins({
            'invalid_sensor': 10
        })
        
        assert result is False
    
    def test_set_sensor_pins_invalid_value(self, config_manager):
        """Should reject non-integer pin values."""
        manager = config_manager
        
        result = manager.set_sensor_pins({
            'i2c_scl': "not an int"
        })
        
        assert result is False
        
        result = manager.set_sensor_pins({
            'i2c_scl': 1.5
        })
        
        assert result is False


class TestGetAll:
    """Tests for get_all method."""
    
    def test_get_all_returns_copy(self, config_manager_with_data):
        """Should return a copy of all config data."""
        manager = config_manager_with_data
        
        data = manager.get_all()
        
        assert 'wifi' in data
        assert 'hostname' in data
        assert 'board' in data
        assert 'timezone' in data
        assert 'sensor_pins' in data
    
    def test_get_all_is_copy(self, config_manager_with_data):
        """Modifying returned data should not affect original."""
        manager = config_manager_with_data
        
        data = manager.get_all()
        data['hostname'] = 'modified'
        
        assert manager.get_hostname() == 'test-esp32'  # Original unchanged


class TestSaveConfig:
    """Tests for save_config method."""
    
    def test_save_config_success(self, config_manager):
        """Should return True on successful save."""
        manager = config_manager
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = manager.save_config()
        
        assert result is True
        mock_file.assert_called_once()
    
    def test_save_config_failure(self, config_manager):
        """Should return False on save failure."""
        manager = config_manager
        
        with patch('builtins.open', side_effect=OSError("Permission denied")):
            result = manager.save_config()
        
        assert result is False
    
    def test_save_config_writes_json(self, config_manager):
        """Should write JSON data to file."""
        manager = config_manager
        manager.set_hostname("test-host")
        
        written_data = []
        
        def mock_dump(data, f):
            written_data.append(data)
        
        with patch('builtins.open', mock_open()):
            with patch('json.dump', mock_dump):
                manager.save_config()
        
        assert len(written_data) == 1
        assert written_data[0]['hostname'] == 'test-host'


class TestDefaultValues:
    """Tests for default configuration values."""
    
    def test_defaults_structure(self, config_manager):
        """Should have correct default structure."""
        manager = config_manager
        
        defaults = manager._get_defaults()
        
        assert 'wifi' in defaults
        assert 'ssid' in defaults['wifi']
        assert 'password' in defaults['wifi']
        assert 'hostname' in defaults
        assert 'board' in defaults
        assert 'timezone' in defaults
        assert 'name' in defaults['timezone']
        assert 'offset_seconds' in defaults['timezone']
        assert 'sensor_pins' in defaults
    
    def test_defaults_wifi_is_none(self, config_manager):
        """WiFi credentials should default to None."""
        manager = config_manager
        
        defaults = manager._get_defaults()
        
        assert defaults['wifi']['ssid'] is None
        assert defaults['wifi']['password'] is None
    
    def test_defaults_hostname(self, config_manager):
        """Hostname should default to 'esp32'."""
        manager = config_manager
        
        defaults = manager._get_defaults()
        
        assert defaults['hostname'] == 'esp32'
    
    def test_defaults_timezone_utc(self, config_manager):
        """Timezone should default to UTC."""
        manager = config_manager
        
        defaults = manager._get_defaults()
        
        assert defaults['timezone']['name'] == 'UTC'
        assert defaults['timezone']['offset_seconds'] == 0
    
    def test_defaults_sensor_pins_disabled(self, config_manager):
        """Sensor pins should default to -1 (disabled)."""
        manager = config_manager
        
        defaults = manager._get_defaults()
        pins = defaults['sensor_pins']
        
        assert pins['i2c_scl'] == -1
        assert pins['i2c_sda'] == -1
        assert pins['ds18b20'] == -1
        assert pins['photo_sensor'] == -1
        assert pins['light_switch'] == -1
        assert pins['reset_switch'] == -1

