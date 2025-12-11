"""
Unit tests for RelayManager - relay operations, inversion logic, error tracking.

Run with: pytest tests/test_relays.py -v
"""

import sys
import json
import pytest
from unittest.mock import MagicMock, patch, mock_open


# Mock MicroPython-specific modules
sys.modules['machine'] = MagicMock()


class MockPin:
    """Mock for machine.Pin."""
    
    OUT = 1
    IN = 0
    
    def __init__(self, pin_num, mode=None):
        self.pin_num = pin_num
        self.mode = mode
        self._value = 0
    
    def value(self, val=None):
        if val is None:
            return self._value
        self._value = val


@pytest.fixture
def mock_machine():
    """Setup mock machine module."""
    mock = MagicMock()
    mock.Pin = MockPin
    mock.Pin.OUT = MockPin.OUT
    mock.Pin.IN = MockPin.IN
    sys.modules['machine'] = mock
    return mock


@pytest.fixture
def relay_manager(mock_machine, tmp_path):
    """Create a RelayManager with mocked dependencies."""
    # Create a temp config file
    config_file = tmp_path / "relays.json"
    
    # Add src to path
    import os
    src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    # Reload the module to pick up mocks
    if 'relays' in sys.modules:
        del sys.modules['relays']
    
    # Patch CONFIG_FILE before import
    with patch('builtins.open', mock_open(read_data='{"relays": []}')):
        from relays import RelayManager
        
        # Create instance with patched file operations
        manager = RelayManager()
        manager.CONFIG_FILE = str(config_file)
        
        yield manager, config_file


class TestRelayManagerInit:
    """Tests for RelayManager initialization."""
    
    def test_init_empty_config(self, relay_manager):
        """Manager should initialize with empty relays when no config."""
        manager, _ = relay_manager
        
        assert manager.relays == []
        assert manager.pins == {}
    
    def test_init_with_config(self, mock_machine, tmp_path):
        """Manager should load relays from config file."""
        config_data = {
            "relays": [
                {
                    "pin": 5,
                    "label": "Light",
                    "isInverted": False,
                    "defaultValue": True,
                    "defaultAuto": False,
                    "rule": '["NOP"]'
                }
            ]
        }
        
        import os
        src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        if 'relays' in sys.modules:
            del sys.modules['relays']
        
        with patch('builtins.open', mock_open(read_data=json.dumps(config_data))):
            from relays import RelayManager
            manager = RelayManager()
        
        assert len(manager.relays) == 1
        assert manager.relays[0]['label'] == "Light"
        assert manager.relays[0]['value'] == True  # From defaultValue
        assert manager.relays[0]['auto'] == False  # From defaultAuto
    
    def test_init_adds_runtime_fields(self, mock_machine):
        """Manager should add runtime fields to loaded relays."""
        config_data = {
            "relays": [
                {
                    "pin": 5,
                    "label": "Light",
                    "isInverted": False
                }
            ]
        }
        
        import os
        src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        if 'relays' in sys.modules:
            del sys.modules['relays']
        
        with patch('builtins.open', mock_open(read_data=json.dumps(config_data))):
            from relays import RelayManager
            manager = RelayManager()
        
        # Runtime fields should be added
        assert 'value' in manager.relays[0]
        assert 'auto' in manager.relays[0]
        assert 'last_error' in manager.relays[0]


class TestGetRelays:
    """Tests for get_relays method."""
    
    def test_get_relays_returns_dict(self, relay_manager):
        """get_relays should return dict with 'relays' key."""
        manager, _ = relay_manager
        
        result = manager.get_relays()
        
        assert isinstance(result, dict)
        assert 'relays' in result
        assert isinstance(result['relays'], list)
    
    def test_get_relays_returns_all_relays(self, relay_manager):
        """get_relays should return all configured relays."""
        manager, _ = relay_manager
        
        manager.relays = [
            {'pin': 5, 'label': 'Light1', 'value': True, 'auto': False},
            {'pin': 6, 'label': 'Light2', 'value': False, 'auto': True},
        ]
        
        result = manager.get_relays()
        
        assert len(result['relays']) == 2


class TestGetRelayByLabel:
    """Tests for get_relay_by_label method."""
    
    def test_get_existing_relay(self, relay_manager):
        """Should return relay with matching label."""
        manager, _ = relay_manager
        
        manager.relays = [
            {'pin': 5, 'label': 'Light', 'value': True},
            {'pin': 6, 'label': 'Fan', 'value': False},
        ]
        
        relay = manager.get_relay_by_label('Light')
        
        assert relay is not None
        assert relay['label'] == 'Light'
        assert relay['pin'] == 5
    
    def test_get_nonexistent_relay(self, relay_manager):
        """Should return None for non-existent label."""
        manager, _ = relay_manager
        
        manager.relays = [
            {'pin': 5, 'label': 'Light', 'value': True},
        ]
        
        relay = manager.get_relay_by_label('NonExistent')
        
        assert relay is None


class TestSetRelayByLabel:
    """Tests for set_relay_by_label method."""
    
    def test_set_relay_state_true(self, relay_manager):
        """Should set relay value to True."""
        manager, _ = relay_manager
        
        manager.relays = [
            {'pin': 5, 'label': 'Light', 'value': False, 'auto': True, 'isInverted': False},
        ]
        manager.pins[5] = MockPin(5, MockPin.OUT)
        
        result = manager.set_relay_by_label('Light', True)
        
        assert result is True
        assert manager.relays[0]['value'] is True
        assert manager.relays[0]['auto'] is False  # Auto mode disabled by default
    
    def test_set_relay_state_false(self, relay_manager):
        """Should set relay value to False."""
        manager, _ = relay_manager
        
        manager.relays = [
            {'pin': 5, 'label': 'Light', 'value': True, 'auto': False, 'isInverted': False},
        ]
        manager.pins[5] = MockPin(5, MockPin.OUT)
        
        result = manager.set_relay_by_label('Light', False)
        
        assert result is True
        assert manager.relays[0]['value'] is False
    
    def test_set_relay_keeps_auto_mode(self, relay_manager):
        """Should keep auto mode when keep_auto=True."""
        manager, _ = relay_manager
        
        manager.relays = [
            {'pin': 5, 'label': 'Light', 'value': False, 'auto': True, 'isInverted': False},
        ]
        manager.pins[5] = MockPin(5, MockPin.OUT)
        
        manager.set_relay_by_label('Light', True, keep_auto=True)
        
        assert manager.relays[0]['auto'] is True
    
    def test_set_relay_disables_auto_by_default(self, relay_manager):
        """Should disable auto mode by default."""
        manager, _ = relay_manager
        
        manager.relays = [
            {'pin': 5, 'label': 'Light', 'value': False, 'auto': True, 'isInverted': False},
        ]
        manager.pins[5] = MockPin(5, MockPin.OUT)
        
        manager.set_relay_by_label('Light', True)
        
        assert manager.relays[0]['auto'] is False
    
    def test_set_nonexistent_relay(self, relay_manager):
        """Should return False for non-existent label."""
        manager, _ = relay_manager
        
        manager.relays = []
        
        result = manager.set_relay_by_label('NonExistent', True)
        
        assert result is False


class TestPhysicalState:
    """Tests for set_physical_state and inversion logic."""
    
    def test_normal_relay_on(self, relay_manager):
        """Normal relay: value True should set GPIO HIGH (1)."""
        manager, _ = relay_manager
        
        pin = MockPin(5, MockPin.OUT)
        manager.pins[5] = pin
        
        manager.set_physical_state(5, True, is_inverted=False)
        
        assert pin._value == 1
    
    def test_normal_relay_off(self, relay_manager):
        """Normal relay: value False should set GPIO LOW (0)."""
        manager, _ = relay_manager
        
        pin = MockPin(5, MockPin.OUT)
        manager.pins[5] = pin
        
        manager.set_physical_state(5, False, is_inverted=False)
        
        assert pin._value == 0
    
    def test_inverted_relay_on(self, relay_manager):
        """Inverted relay: value True should set GPIO LOW (0)."""
        manager, _ = relay_manager
        
        pin = MockPin(5, MockPin.OUT)
        manager.pins[5] = pin
        
        manager.set_physical_state(5, True, is_inverted=True)
        
        assert pin._value == 0
    
    def test_inverted_relay_off(self, relay_manager):
        """Inverted relay: value False should set GPIO HIGH (1)."""
        manager, _ = relay_manager
        
        pin = MockPin(5, MockPin.OUT)
        manager.pins[5] = pin
        
        manager.set_physical_state(5, False, is_inverted=True)
        
        assert pin._value == 1
    
    def test_physical_state_unknown_pin(self, relay_manager):
        """Should silently ignore unknown pins."""
        manager, _ = relay_manager
        
        # Should not raise exception
        manager.set_physical_state(999, True, is_inverted=False)


class TestRelayErrors:
    """Tests for relay error tracking."""
    
    def test_set_relay_error(self, relay_manager):
        """Should set error message for relay."""
        manager, _ = relay_manager
        
        manager.relays = [
            {'pin': 5, 'label': 'Light', 'value': True, 'last_error': None},
        ]
        
        result = manager.set_relay_error('Light', 'Sensor read failed')
        
        assert result is True
        assert manager.relays[0]['last_error'] == 'Sensor read failed'
    
    def test_set_error_nonexistent_relay(self, relay_manager):
        """Should return False for non-existent label."""
        manager, _ = relay_manager
        
        manager.relays = []
        
        result = manager.set_relay_error('NonExistent', 'Error')
        
        assert result is False
    
    def test_clear_relay_error(self, relay_manager):
        """Should clear error message for relay."""
        manager, _ = relay_manager
        
        manager.relays = [
            {'pin': 5, 'label': 'Light', 'value': True, 'last_error': 'Some error'},
        ]
        
        result = manager.clear_relay_error('Light')
        
        assert result is True
        assert manager.relays[0]['last_error'] is None
    
    def test_clear_error_nonexistent_relay(self, relay_manager):
        """Should return False for non-existent label."""
        manager, _ = relay_manager
        
        manager.relays = []
        
        result = manager.clear_relay_error('NonExistent')
        
        assert result is False


class TestUpdateConfig:
    """Tests for update_config method."""
    
    def test_update_config_replaces_relays(self, relay_manager):
        """Should replace relay list with new config."""
        manager, _ = relay_manager
        
        manager.relays = [
            {'pin': 5, 'label': 'OldRelay', 'value': True},
        ]
        
        new_relays = [
            {'pin': 6, 'label': 'NewRelay'},
            {'pin': 7, 'label': 'AnotherRelay'},
        ]
        
        with patch.object(manager, 'save_config', return_value=True):
            with patch.object(manager, '_setup_pins'):
                result = manager.update_config(new_relays)
        
        assert result is True
        assert len(manager.relays) == 2
        assert manager.relays[0]['label'] == 'NewRelay'
    
    def test_update_config_adds_runtime_fields(self, relay_manager):
        """Should add runtime fields to new relays."""
        manager, _ = relay_manager
        
        new_relays = [
            {'pin': 6, 'label': 'NewRelay'},
        ]
        
        with patch.object(manager, 'save_config', return_value=True):
            with patch.object(manager, '_setup_pins'):
                manager.update_config(new_relays)
        
        assert manager.relays[0]['value'] is False
        assert manager.relays[0]['auto'] is False
        assert manager.relays[0]['last_error'] is None
    
    def test_update_config_invalid_type(self, relay_manager):
        """Should return False for non-list input."""
        manager, _ = relay_manager
        
        result = manager.update_config("not a list")
        
        assert result is False
        
        result = manager.update_config({'relays': []})
        
        assert result is False


class TestSaveConfig:
    """Tests for save_config method."""
    
    def test_save_config_excludes_runtime_fields(self, relay_manager):
        """Saved config should not include runtime fields."""
        manager, config_file = relay_manager
        
        manager.relays = [
            {
                'pin': 5,
                'label': 'Light',
                'isInverted': True,
                'defaultValue': True,
                'defaultAuto': True,
                'rule': 'get_temperature() > 25',
                'value': False,  # Runtime - should not be saved
                'auto': True,    # Runtime - should not be saved
                'last_error': 'Error',  # Runtime - should not be saved
            },
        ]
        
        # Actually write to the temp file
        manager.CONFIG_FILE = str(config_file)
        
        with patch('builtins.open', mock_open()) as mock_file:
            # Mock json.dump to capture what would be written
            import json as json_module
            original_dump = json_module.dump
            written_data = {}
            
            def capture_dump(data, f):
                written_data.update(data)
            
            with patch.object(json_module, 'dump', capture_dump):
                manager.save_config()
        
        # Check that runtime fields are excluded
        saved_relay = written_data['relays'][0]
        assert 'value' not in saved_relay
        assert 'auto' not in saved_relay
        assert 'last_error' not in saved_relay
        
        # Check that persistent fields are included
        assert saved_relay['pin'] == 5
        assert saved_relay['label'] == 'Light'
        assert saved_relay['isInverted'] is True
        assert saved_relay['defaultValue'] is True
        assert saved_relay['defaultAuto'] is True
        assert saved_relay['rule'] == 'get_temperature() > 25'


class TestMultipleRelays:
    """Tests with multiple relays."""
    
    def test_set_specific_relay_in_list(self, relay_manager):
        """Should only modify the targeted relay."""
        manager, _ = relay_manager
        
        manager.relays = [
            {'pin': 5, 'label': 'Light1', 'value': False, 'auto': False, 'isInverted': False},
            {'pin': 6, 'label': 'Light2', 'value': False, 'auto': False, 'isInverted': False},
            {'pin': 7, 'label': 'Fan', 'value': False, 'auto': False, 'isInverted': False},
        ]
        manager.pins[5] = MockPin(5, MockPin.OUT)
        manager.pins[6] = MockPin(6, MockPin.OUT)
        manager.pins[7] = MockPin(7, MockPin.OUT)
        
        manager.set_relay_by_label('Light2', True)
        
        assert manager.relays[0]['value'] is False  # Light1 unchanged
        assert manager.relays[1]['value'] is True   # Light2 changed
        assert manager.relays[2]['value'] is False  # Fan unchanged
    
    def test_get_specific_relay_from_list(self, relay_manager):
        """Should return correct relay from multiple."""
        manager, _ = relay_manager
        
        manager.relays = [
            {'pin': 5, 'label': 'Light1', 'value': True},
            {'pin': 6, 'label': 'Light2', 'value': False},
            {'pin': 7, 'label': 'Fan', 'value': True},
        ]
        
        relay = manager.get_relay_by_label('Fan')
        
        assert relay['pin'] == 7
        assert relay['label'] == 'Fan'
        assert relay['value'] is True

