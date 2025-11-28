"""
Rule engine for evaluating Python-based automation rules.

This module provides safe evaluation of user-defined Python expressions
for controlling relay states based on sensor inputs and time conditions.

Example rules:
- Simple: "get_temperature() > 25"
- Time-based: "time(8, 0) < get_time() < time(18, 0)"
- Complex: "get_temperature() > 25 and get_humidity() < 60"
"""

from instances import instances

class RuleEngine:
    """Evaluates automation rules safely with restricted Python eval."""
    
    def __init__(self):
        """Initialize rule engine.
        
        Uses global instances for sensors and time_sync.
        """
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
    
    def get_current_time_seconds(self):
        """Get current time in seconds since midnight.
        
        Uses TimeSync if available, otherwise falls back to sensor dummy time.
        """
        if instances.time_sync and instances.time_sync.is_synced:
            return instances.time_sync.get_minute_of_day() * 60
        else:
            # Fallback to sensor manager's dummy time
            return instances.sensors.get_time_seconds()
    
    def _get_safe_globals(self):
        """Create a restricted global namespace for eval.
        
        Only includes sensor functions and safe built-ins.
        Blocks dangerous operations like imports, file I/O, etc.
        """
        return {
            # Sensor functions
            'get_temperature': instances.sensors.get_temperature,
            'get_humidity': instances.sensors.get_humidity,
            'get_light_level': instances.sensors.get_light_level,
            'get_switch_state': instances.sensors.get_switch_state,
            'get_reset_switch_state': instances.sensors.get_reset_switch_state,
            'get_time': self.get_current_time_seconds,  # Use real time if available
            
            # Last values (for edge detection)
            'get_last_temperature': instances.sensors.get_last_temperature,
            'get_last_humidity': instances.sensors.get_last_humidity,
            'get_last_light_level': instances.sensors.get_last_light_level,
            'get_last_switch_state': instances.sensors.get_last_switch_state,
            'get_last_reset_switch_state': instances.sensors.get_last_reset_switch_state,
            'get_last_time': instances.sensors.get_last_time,
            
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
        
        Supports both single-line expressions and multi-line statements.
        
        Args:
            rule_code: Python code string (expression or statements)
            
        Returns:
            (valid, error_message) tuple
            
        Example:
            valid, error = engine.validate("get_temperature() > 25")
            valid, error = engine.validate("temp = get_temperature()\ntemp > 25")
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
        
        # Try to compile as expression first (single line)
        try:
            compile(rule_code, '<rule>', 'eval')
            return True, None
        except SyntaxError:
            # Not a valid expression, try as exec (multi-line)
            try:
                compile(rule_code, '<rule>', 'exec')
                return True, None
            except SyntaxError as e:
                return False, f"Syntax error: {e}"
            except Exception as e:
                return False, f"Validation error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def evaluate(self, rule_code):
        """Evaluate a rule and return the result.
        
        Supports both single-line expressions and multi-line statements.
        For multi-line rules, the last expression or a 'result' variable is returned.
        
        Args:
            rule_code: Python code string (expression or statements)
            
        Returns:
            Result of the rule evaluation (True, False, None, or other)
            - True: Turn relay ON
            - False: Turn relay OFF
            - None (or anything else): Keep current state
            
        Raises:
            Exception: If rule evaluation fails
            
        Examples:
            # Single line
            result = engine.evaluate("get_temperature() > 25")
            
            # Multi-line with result variable
            result = engine.evaluate('''
temp = get_temperature()
result = True if temp > 25 else None
''')
            
            # Multi-line with last expression
            result = engine.evaluate('''
temp = get_temperature()
True if temp > 25 else None
''')
        """
        if not rule_code or not rule_code.strip():
            return None
        
        # Use cached compiled code if available
        cache_key = (rule_code, 'eval')
        if cache_key not in self._compiled_cache:
            try:
                # Try to compile as expression first
                self._compiled_cache[cache_key] = compile(rule_code, '<rule>', 'eval')
            except SyntaxError:
                # Not an expression, try as exec (multi-line)
                cache_key = (rule_code, 'exec')
                if cache_key not in self._compiled_cache:
                    try:
                        self._compiled_cache[cache_key] = compile(rule_code, '<rule>', 'exec')
                    except Exception as e:
                        print(f"Rule compilation error: {e}")
                        raise
        
        compiled_code = self._compiled_cache[cache_key]
        mode = cache_key[1]
        
        # Evaluate with restricted globals
        try:
            safe_globals = self._get_safe_globals()
            
            if mode == 'eval':
                # Single expression - return directly
                result = eval(compiled_code, safe_globals, {})
            else:
                # Multi-line statements - use exec
                local_vars = {}
                exec(compiled_code, safe_globals, local_vars)
                
                # Return 'result' variable if it exists, otherwise None
                result = local_vars.get('result', None)
            
            # Return as-is (True, False, None, or other)
            # Don't coerce to boolean - let caller decide what to do with None
            return result
            
        except Exception as e:
            print(f"Rule evaluation error: {e}")
            raise
    
    def evaluate_safe(self, rule_code, default=None):
        """Evaluate a rule with exception handling.
        
        Args:
            rule_code: Python code string (expression or statements)
            default: Default value to return on error (default: None = keep state)
            
        Returns:
            Result of rule evaluation (True/False/None), or default on error
            
        Example:
            result = engine.evaluate_safe("get_temperature() > 25", default=None)
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

