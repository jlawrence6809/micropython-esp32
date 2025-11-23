"""
Rule engine for evaluating Python-based automation rules.

This module provides safe evaluation of user-defined Python expressions
for controlling relay states based on sensor inputs and time conditions.

Example rules:
- Simple: "get_temperature() > 25"
- Time-based: "time(8, 0) < get_time() < time(18, 0)"
- Complex: "get_temperature() > 25 and get_humidity() < 60"
"""

class RuleEngine:
    """Evaluates automation rules safely with restricted Python eval."""
    
    def __init__(self, sensor_manager):
        """Initialize rule engine with sensor manager.
        
        Args:
            sensor_manager: SensorManager instance for reading sensor values
        """
        self.sensors = sensor_manager
        self._compiled_cache = {}  # Cache compiled code objects
        
    def time(self, hour, minute=0, second=0):
        """Helper function to convert time to seconds since midnight.
        
        Args:
            hour: Hour (0-23)
            minute: Minute (0-59)
            second: Second (0-59)
            
        Returns:
            Seconds since midnight
            
        Example:
            time(8, 30) -> 30600  # 8:30 AM
        """
        return hour * 3600 + minute * 60 + second
    
    def _get_safe_globals(self):
        """Create a restricted global namespace for eval.
        
        Only includes sensor functions and safe built-ins.
        Blocks dangerous operations like imports, file I/O, etc.
        """
        return {
            # Sensor functions
            'get_temperature': self.sensors.get_temperature,
            'get_humidity': self.sensors.get_humidity,
            'get_light_level': self.sensors.get_light_level,
            'get_switch_state': self.sensors.get_switch_state,
            'get_time': self.sensors.get_time_seconds,
            
            # Last values (for edge detection)
            'get_last_temperature': self.sensors.get_last_temperature,
            'get_last_humidity': self.sensors.get_last_humidity,
            'get_last_light_level': self.sensors.get_last_light_level,
            'get_last_switch_state': self.sensors.get_last_switch_state,
            
            # Time helper
            'time': self.time,
            
            # Safe built-ins (very limited)
            'True': True,
            'False': False,
            'None': None,
            'abs': abs,
            'min': min,
            'max': max,
            'round': round,
            
            # Block everything else
            '__builtins__': {},
            '__import__': None,
            '__name__': None,
            '__file__': None,
        }
    
    def validate(self, rule_code):
        """Validate a rule without executing it.
        
        Args:
            rule_code: Python expression string
            
        Returns:
            (valid, error_message) tuple
            
        Example:
            valid, error = engine.validate("get_temperature() > 25")
        """
        if not rule_code or not rule_code.strip():
            return False, "Rule is empty"
        
        # Check for obviously dangerous patterns
        dangerous_keywords = [
            'import', 'exec', 'eval', 'compile', 
            'open', 'file', '__', 'globals', 'locals',
            'setattr', 'getattr', 'delattr', 'dir'
        ]
        
        rule_lower = rule_code.lower()
        for keyword in dangerous_keywords:
            if keyword in rule_lower:
                return False, f"Forbidden keyword: {keyword}"
        
        # Try to compile it
        try:
            compile(rule_code, '<rule>', 'eval')
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def evaluate(self, rule_code):
        """Evaluate a rule and return the result.
        
        Args:
            rule_code: Python expression string
            
        Returns:
            Boolean result of the rule evaluation
            
        Raises:
            Exception: If rule evaluation fails
            
        Example:
            result = engine.evaluate("get_temperature() > 25")
        """
        if not rule_code or not rule_code.strip():
            return False
        
        # Use cached compiled code if available
        if rule_code not in self._compiled_cache:
            try:
                self._compiled_cache[rule_code] = compile(rule_code, '<rule>', 'eval')
            except Exception as e:
                print(f"Rule compilation error: {e}")
                raise
        
        compiled_code = self._compiled_cache[rule_code]
        
        # Evaluate with restricted globals
        try:
            result = eval(compiled_code, self._get_safe_globals(), {})
            # Coerce to boolean
            return bool(result)
        except Exception as e:
            print(f"Rule evaluation error: {e}")
            raise
    
    def evaluate_safe(self, rule_code, default=False):
        """Evaluate a rule with exception handling.
        
        Args:
            rule_code: Python expression string
            default: Default value to return on error
            
        Returns:
            Boolean result, or default on error
            
        Example:
            result = engine.evaluate_safe("get_temperature() > 25", default=False)
        """
        try:
            return self.evaluate(rule_code)
        except Exception as e:
            print(f"Rule error (returning {default}): {e}")
            return default
    
    def clear_cache(self):
        """Clear the compiled code cache.
        
        Call this when rules are updated to free memory.
        """
        self._compiled_cache.clear()

