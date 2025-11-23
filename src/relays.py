import machine
import json
import os

CONFIG_FILE = 'relays.json'

class RelayManager:
    def __init__(self):
        self.relays = []
        self.pins = {}  # Map pin number to machine.Pin object
        self.load_config()

    def load_config(self):
        """Load relay configuration from JSON file."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                self.relays = data.get('relays', [])
                
                # Initialize runtime state for each relay
                for relay in self.relays:
                    # Initialize value from defaultValue if not present
                    if 'value' not in relay:
                        relay['value'] = relay.get('defaultValue', False)
                    
                    # Initialize auto mode (default to manual/forced)
                    if 'auto' not in relay:
                        relay['auto'] = False
                            
        except (OSError, ValueError):
            print("No relay config found, using default empty config.")
            self.relays = []
            
        self._setup_pins()

    def save_config(self):
        """Save current configuration to JSON file (without runtime state)."""
        # Remove runtime-only fields (value, auto) before saving
        relays_for_save = []
        for relay in self.relays:
            relay_copy = {
                'pin': relay['pin'],
                'label': relay['label'],
                'isInverted': relay.get('isInverted', False),
                'defaultValue': relay.get('defaultValue', False),
                'rule': relay.get('rule', '["NOP"]')
            }
            relays_for_save.append(relay_copy)
            
        data = {'relays': relays_for_save}
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f)
            return True
        except OSError as e:
            print(f"Failed to save relay config: {e}")
            return False

    def _setup_pins(self):
        """Initialize GPIO pins based on configuration."""
        for relay in self.relays:
            pin_num = relay.get('pin')
            if pin_num is not None and pin_num >= 0:
                try:
                    # Configure pin as output
                    pin = machine.Pin(pin_num, machine.Pin.OUT)
                    self.pins[pin_num] = pin
                    
                    # Set physical state based on current value
                    value = relay.get('value', False)
                    self.set_physical_state(pin_num, value, relay.get('isInverted', False))
                    
                except ValueError as e:
                    print(f"Invalid PIN {pin_num}: {e}")

    def set_physical_state(self, pin_num, value, is_inverted):
        """Set the physical GPIO state, handling inversion logic."""
        if pin_num not in self.pins:
            return
        
        pin = self.pins[pin_num]
        # If inverted: value True means GPIO LOW (0), value False means GPIO HIGH (1)
        # If normal:   value True means GPIO HIGH (1), value False means GPIO LOW (0)
        
        if is_inverted:
            physical_value = 0 if value else 1
        else:
            physical_value = 1 if value else 0
            
        pin.value(physical_value)

    def get_relays(self):
        """Return list of all relay configurations."""
        return {'relays': self.relays}

    def update_config(self, new_relays):
        """Update the entire relay configuration."""
        if not isinstance(new_relays, list):
            return False

        # Update relays, preserving runtime state where appropriate
        self.relays = new_relays
        
        # Ensure all relays have required runtime fields
        for relay in self.relays:
            if 'value' not in relay:
                relay['value'] = False
            if 'auto' not in relay:
                relay['auto'] = False
                
        self.save_config()
        self._setup_pins()  # Re-configure pins with new values
        return True

    def set_relay_by_label(self, label, state):
        """Set a relay state by its label (updates value and sets to manual mode)."""
        found = False
        for relay in self.relays:
            if relay.get('label') == label:
                # Update value
                relay['value'] = state
                
                # Set to manual mode (not auto)
                relay['auto'] = False
                
                # Update physical pin
                self.set_physical_state(
                    relay['pin'], 
                    relay['value'], 
                    relay.get('isInverted', False)
                )
                found = True
        
        return found

    def get_relay_by_label(self, label):
        """Get a relay configuration by its label."""
        for relay in self.relays:
            if relay.get('label') == label:
                return relay
        return None
