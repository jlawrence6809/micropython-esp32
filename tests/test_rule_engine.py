"""
Unit tests for RuleEngine validation, evaluation, security, and caching.

Run with: pytest tests/test_rule_engine.py -v
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
        
        self.last_temperature = 24.0
        self.last_humidity = 48.0
        self.last_light_level = 1800
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
    """Create mock instances."""
    return MockInstanceManager()


@pytest.fixture
def rule_engine(mock_instances):
    """Create a RuleEngine with mocked dependencies."""
    with patch.dict(sys.modules, {'instances': MagicMock()}):
        sys.modules['instances'].instances = mock_instances
        
        if 'rule_engine' in sys.modules:
            del sys.modules['rule_engine']
        
        import os
        src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        from rule_engine import RuleEngine
        engine = RuleEngine()
        
        yield engine, mock_instances


class TestRuleValidation:
    """Tests for rule validation."""
    
    def test_validate_empty_rule(self, rule_engine):
        """Empty rules should be invalid."""
        engine, _ = rule_engine
        
        valid, error = engine.validate("")
        assert valid is False
        assert "empty" in error.lower()
        
        valid, error = engine.validate("   ")
        assert valid is False
        assert "empty" in error.lower()
        
        valid, error = engine.validate(None)
        assert valid is False
    
    def test_validate_simple_expression(self, rule_engine):
        """Simple expressions should be valid."""
        engine, _ = rule_engine
        
        valid, error = engine.validate("True")
        assert valid is True
        assert error is None
        
        valid, error = engine.validate("1 + 1")
        assert valid is True
        
        valid, error = engine.validate("get_temperature() > 25")
        assert valid is True
    
    def test_validate_multiline_rule(self, rule_engine):
        """Multi-line rules should be valid."""
        engine, _ = rule_engine
        
        rule = """
temp = get_temperature()
result = temp > 25
"""
        valid, error = engine.validate(rule)
        assert valid is True
    
    def test_validate_syntax_error(self, rule_engine):
        """Rules with syntax errors should be invalid."""
        engine, _ = rule_engine
        
        valid, error = engine.validate("if True")
        assert valid is False
        assert "syntax" in error.lower()
        
        valid, error = engine.validate("def foo(:")
        assert valid is False
    
    def test_validate_forbidden_import(self, rule_engine):
        """Import statements should be forbidden."""
        engine, _ = rule_engine
        
        valid, error = engine.validate("import os")
        assert valid is False
        assert "import" in error.lower()
    
    def test_validate_forbidden_exec(self, rule_engine):
        """Exec/eval should be forbidden."""
        engine, _ = rule_engine
        
        valid, error = engine.validate("exec('print(1)')")
        assert valid is False
        assert "exec" in error.lower()
        
        valid, error = engine.validate("eval('1+1')")
        assert valid is False
        assert "eval" in error.lower()
    
    def test_validate_forbidden_dunder(self, rule_engine):
        """Dunder attributes should be forbidden."""
        engine, _ = rule_engine
        
        valid, error = engine.validate("x.__class__")
        assert valid is False
        assert "__" in error.lower()
        
        valid, error = engine.validate("__builtins__")
        assert valid is False
    
    def test_validate_forbidden_file_operations(self, rule_engine):
        """File operations should be forbidden."""
        engine, _ = rule_engine
        
        valid, error = engine.validate("open('test.txt')")
        assert valid is False
        assert "open" in error.lower()
    
    def test_validate_forbidden_introspection(self, rule_engine):
        """Introspection functions should be forbidden."""
        engine, _ = rule_engine
        
        valid, error = engine.validate("globals()")
        assert valid is False
        
        valid, error = engine.validate("locals()")
        assert valid is False
        
        valid, error = engine.validate("dir()")
        assert valid is False
    
    def test_validate_forbidden_setattr(self, rule_engine):
        """setattr/getattr/delattr should be forbidden."""
        engine, _ = rule_engine
        
        valid, error = engine.validate("setattr(x, 'a', 1)")
        assert valid is False
        
        valid, error = engine.validate("getattr(x, 'a')")
        assert valid is False
        
        valid, error = engine.validate("delattr(x, 'a')")
        assert valid is False


class TestRuleEvaluation:
    """Tests for rule evaluation."""
    
    def test_evaluate_empty_rule(self, rule_engine):
        """Empty rules should return None."""
        engine, _ = rule_engine
        
        assert engine.evaluate("") is None
        assert engine.evaluate("   ") is None
        assert engine.evaluate(None) is None
    
    def test_evaluate_simple_boolean(self, rule_engine):
        """Simple boolean expressions should work."""
        engine, _ = rule_engine
        
        assert engine.evaluate("True") is True
        assert engine.evaluate("False") is False
        assert engine.evaluate("None") is None
    
    def test_evaluate_arithmetic(self, rule_engine):
        """Arithmetic expressions should work."""
        engine, _ = rule_engine
        
        assert engine.evaluate("1 + 1") == 2
        assert engine.evaluate("10 - 3") == 7
        assert engine.evaluate("2 * 3") == 6
        assert engine.evaluate("10 / 2") == 5.0
    
    def test_evaluate_comparison(self, rule_engine):
        """Comparison expressions should work."""
        engine, _ = rule_engine
        
        assert engine.evaluate("5 > 3") is True
        assert engine.evaluate("5 < 3") is False
        assert engine.evaluate("5 >= 5") is True
        assert engine.evaluate("5 <= 4") is False
        assert engine.evaluate("5 == 5") is True
        assert engine.evaluate("5 != 3") is True
    
    def test_evaluate_logical_operators(self, rule_engine):
        """Logical operators should work."""
        engine, _ = rule_engine
        
        assert engine.evaluate("True and True") is True
        assert engine.evaluate("True and False") is False
        assert engine.evaluate("True or False") is True
        assert engine.evaluate("not True") is False
        assert engine.evaluate("not False") is True
    
    def test_evaluate_safe_builtins(self, rule_engine):
        """Safe built-in functions should work."""
        engine, _ = rule_engine
        
        assert engine.evaluate("abs(-5)") == 5
        assert engine.evaluate("min(3, 1, 2)") == 1
        assert engine.evaluate("max(3, 1, 2)") == 3
        assert engine.evaluate("round(3.7)") == 4
        assert engine.evaluate("round(3.14159, 2)") == 3.14
    
    def test_evaluate_sensor_functions(self, rule_engine):
        """Sensor functions should be accessible."""
        engine, mocks = rule_engine
        
        mocks.sensors.temperature = 28.5
        assert engine.evaluate("get_temperature()") == 28.5
        
        mocks.sensors.humidity = 65.0
        assert engine.evaluate("get_humidity()") == 65.0
        
        mocks.sensors.light_level = 3000
        assert engine.evaluate("get_light_level()") == 3000
        
        mocks.sensors.switch_state = True
        assert engine.evaluate("get_switch_state()") is True
    
    def test_evaluate_last_sensor_functions(self, rule_engine):
        """Last sensor value functions should be accessible."""
        engine, mocks = rule_engine
        
        mocks.sensors.last_temperature = 26.0
        assert engine.evaluate("get_last_temperature()") == 26.0
        
        mocks.sensors.last_humidity = 55.0
        assert engine.evaluate("get_last_humidity()") == 55.0
    
    def test_evaluate_temperature_rule(self, rule_engine):
        """Temperature-based rules should work."""
        engine, mocks = rule_engine
        
        mocks.sensors.temperature = 30.0
        assert engine.evaluate("get_temperature() > 25") is True
        
        mocks.sensors.temperature = 20.0
        assert engine.evaluate("get_temperature() > 25") is False
    
    def test_evaluate_combined_rule(self, rule_engine):
        """Combined sensor rules should work."""
        engine, mocks = rule_engine
        
        mocks.sensors.temperature = 30.0
        mocks.sensors.humidity = 40.0
        
        assert engine.evaluate("get_temperature() > 25 and get_humidity() < 50") is True
        
        mocks.sensors.humidity = 60.0
        assert engine.evaluate("get_temperature() > 25 and get_humidity() < 50") is False
    
    def test_evaluate_multiline_with_result(self, rule_engine):
        """Multi-line rules with result variable should work."""
        engine, mocks = rule_engine
        
        mocks.sensors.temperature = 30.0
        
        rule = """
temp = get_temperature()
result = temp > 25
"""
        assert engine.evaluate(rule) is True
        
        mocks.sensors.temperature = 20.0
        engine.clear_cache()  # Clear cache so rule is re-evaluated
        assert engine.evaluate(rule) is False
    
    def test_evaluate_multiline_with_conditional_result(self, rule_engine):
        """Multi-line rules with conditional result should work."""
        engine, mocks = rule_engine
        
        mocks.sensors.temperature = 30.0
        
        rule = """
temp = get_temperature()
if temp > 28:
    result = True
elif temp < 22:
    result = False
else:
    result = None
"""
        assert engine.evaluate(rule) is True
        
        mocks.sensors.temperature = 20.0
        engine.clear_cache()
        assert engine.evaluate(rule) is False
        
        mocks.sensors.temperature = 25.0
        engine.clear_cache()
        assert engine.evaluate(rule) is None
    
    def test_evaluate_multiline_without_result_returns_none(self, rule_engine):
        """Multi-line rules without result variable should return None."""
        engine, mocks = rule_engine
        
        rule = """
temp = get_temperature()
x = temp + 5
"""
        assert engine.evaluate(rule) is None


class TestRuleSecurity:
    """Tests for security restrictions in rule evaluation."""
    
    def test_cannot_access_builtins(self, rule_engine):
        """Should not be able to access __builtins__."""
        engine, _ = rule_engine
        
        # These should raise exceptions due to restricted globals
        with pytest.raises(Exception):
            engine.evaluate("print('hello')")
        
        with pytest.raises(Exception):
            engine.evaluate("len([1,2,3])")
    
    def test_cannot_import(self, rule_engine):
        """Should not be able to import modules."""
        engine, _ = rule_engine
        
        # Even if validation is bypassed somehow
        with pytest.raises(Exception):
            engine.evaluate("__import__('os')")
    
    def test_cannot_access_file_system(self, rule_engine):
        """Should not be able to access file system."""
        engine, _ = rule_engine
        
        with pytest.raises(Exception):
            engine.evaluate("open('/etc/passwd')")


class TestRuleCaching:
    """Tests for compiled rule caching."""
    
    def test_rules_are_cached(self, rule_engine):
        """Compiled rules should be cached."""
        engine, _ = rule_engine
        
        rule = "1 + 1"
        
        # First evaluation
        engine.evaluate(rule)
        assert len(engine._compiled_cache) == 1
        
        # Second evaluation should use cache
        engine.evaluate(rule)
        assert len(engine._compiled_cache) == 1
    
    def test_different_rules_cached_separately(self, rule_engine):
        """Different rules should be cached separately."""
        engine, _ = rule_engine
        
        engine.evaluate("1 + 1")
        engine.evaluate("2 + 2")
        
        assert len(engine._compiled_cache) == 2
    
    def test_clear_cache(self, rule_engine):
        """clear_cache should empty the cache."""
        engine, _ = rule_engine
        
        engine.evaluate("1 + 1")
        engine.evaluate("2 + 2")
        
        assert len(engine._compiled_cache) == 2
        
        engine.clear_cache()
        
        assert len(engine._compiled_cache) == 0


class TestEvaluateSafe:
    """Tests for evaluate_safe method."""
    
    def test_evaluate_safe_returns_result(self, rule_engine):
        """evaluate_safe should return the result on success."""
        engine, _ = rule_engine
        
        assert engine.evaluate_safe("True") is True
        assert engine.evaluate_safe("False") is False
        assert engine.evaluate_safe("1 + 1") == 2
    
    def test_evaluate_safe_returns_default_on_error(self, rule_engine):
        """evaluate_safe should return default on error."""
        engine, _ = rule_engine
        
        # Invalid code that would raise an exception
        result = engine.evaluate_safe("undefined_variable", default=None)
        assert result is None
        
        result = engine.evaluate_safe("undefined_variable", default=False)
        assert result is False
    
    def test_evaluate_safe_with_none_default(self, rule_engine):
        """evaluate_safe with None default should return None on error."""
        engine, _ = rule_engine
        
        result = engine.evaluate_safe("undefined_var")
        assert result is None


class TestComplexRules:
    """Tests for complex real-world rules."""
    
    def test_temperature_hysteresis_rule(self, rule_engine):
        """Test temperature rule with hysteresis."""
        engine, mocks = rule_engine
        
        rule = """
temp = get_temperature()
last_temp = get_last_temperature()

# Turn on if rising above 28, turn off if falling below 25
if temp > 28 and last_temp <= 28:
    result = True
elif temp < 25 and last_temp >= 25:
    result = False
else:
    result = None
"""
        # Rising above threshold
        mocks.sensors.temperature = 29.0
        mocks.sensors.last_temperature = 27.0
        assert engine.evaluate(rule) is True
        
        # Falling below threshold
        engine.clear_cache()
        mocks.sensors.temperature = 24.0
        mocks.sensors.last_temperature = 26.0
        assert engine.evaluate(rule) is False
        
        # Staying in between - no change
        engine.clear_cache()
        mocks.sensors.temperature = 26.0
        mocks.sensors.last_temperature = 26.0
        assert engine.evaluate(rule) is None
    
    def test_light_level_rule(self, rule_engine):
        """Test light level based rule."""
        engine, mocks = rule_engine
        
        # Turn on lights when dark (low ADC value)
        mocks.sensors.light_level = 500
        assert engine.evaluate("get_light_level() < 1000") is True
        
        # Turn off lights when bright
        mocks.sensors.light_level = 3500
        assert engine.evaluate("get_light_level() < 1000") is False
    
    def test_humidity_and_temperature_combo(self, rule_engine):
        """Test combined humidity and temperature rule."""
        engine, mocks = rule_engine
        
        rule = "get_temperature() > 25 and get_humidity() > 70"
        
        # Hot and humid
        mocks.sensors.temperature = 30.0
        mocks.sensors.humidity = 80.0
        assert engine.evaluate(rule) is True
        
        # Hot but dry
        mocks.sensors.temperature = 30.0
        mocks.sensors.humidity = 50.0
        assert engine.evaluate(rule) is False
        
        # Cool and humid
        mocks.sensors.temperature = 20.0
        mocks.sensors.humidity = 80.0
        assert engine.evaluate(rule) is False
    
    def test_ternary_expression(self, rule_engine):
        """Test ternary expression in rules."""
        engine, mocks = rule_engine
        
        mocks.sensors.temperature = 30.0
        assert engine.evaluate("True if get_temperature() > 25 else False") is True
        
        mocks.sensors.temperature = 20.0
        assert engine.evaluate("True if get_temperature() > 25 else False") is False
    
    def test_none_for_no_change(self, rule_engine):
        """Test returning None to indicate no state change."""
        engine, mocks = rule_engine
        
        rule = "True if get_temperature() > 30 else (False if get_temperature() < 20 else None)"
        
        # Hot - turn on
        mocks.sensors.temperature = 35.0
        assert engine.evaluate(rule) is True
        
        # Cold - turn off
        mocks.sensors.temperature = 15.0
        assert engine.evaluate(rule) is False
        
        # Moderate - no change
        mocks.sensors.temperature = 25.0
        assert engine.evaluate(rule) is None

