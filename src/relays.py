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
                # Copy defaultValue to currentValue for all relays, if present
                for relay in self.relays:
                    if 'defaultValue' in relay:
                        relay['currentValue'] = relay['defaultValue']
        except (OSError, ValueError):
            print("No relay config found, using default empty config.")
            self.relays = []
            # Nothing to inherit currentValue in this case
            
        self._setup_pins()

    def save_config(self):
        """Save current configuration to JSON file."""
        # Remove 'currentValue' from each relay for saving only (not mutating self.relays)
        relays_for_save = []
        for relay in self.relays:
            relay_copy = relay.copy()
            relay_copy.pop('currentValue', None)
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
        # Identify pins no longer in use to release them? 
        # MicroPython doesn't easily let you "deinit" a pin to free it completely,
        # but re-initializing it is usually fine.
        
        for relay in self.relays:
            pin_num = relay.get('pin')
            if pin_num is not None:
                try:
                    # Configure pin as output
                    pin = machine.Pin(pin_num, machine.Pin.OUT)
                    self.pins[pin_num] = pin
                    
                    # Set initial state (respecting default value and inversion)
                    current_val = relay.get('currentValue', 0)
                    self.set_physical_state(pin_num, current_val, relay.get('isInverted', False))
                    
                    # Update current value in memory to match
                    relay['currentValue'] = current_val
                except ValueError as e:
                    print(f"Invalid PIN {pin_num}: {e}")

    def set_physical_state(self, pin_num, value, is_inverted):
        """Set the physical GPIO state, handling inversion logic."""
        if pin_num not in self.pins:
            return
        
        pin = self.pins[pin_num]
        # If inverted: value 1 means GPIO LOW (0), value 0 means GPIO HIGH (1)
        # If normal:   value 1 means GPIO HIGH (1), value 0 means GPIO LOW (0)
        
        physical_value = 0
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
        # Validate structure roughly
        if not isinstance(new_relays, list):
            return False

        # update the relays
        self.relays = new_relays
        self.save_config()
        self._setup_pins()  # Re-configure pins
        return True

    def set_relay_by_label(self, label, state):
        """Set a relay state by its label."""
        found = False
        for relay in self.relays:
            if relay.get('label') == label:
                relay['currentValue'] = 1 if state else 0
                self.set_physical_state(
                    relay['pin'], 
                    relay['currentValue'], 
                    relay.get('isInverted', False)
                )
                found = True
                # Don't break, in case multiple relays share a label? 
                # (Original C code assumes unique labels or first match, let's do all matches for safety)
        
        # If we changed state, should we save it? 
        # Original code: 'runtime_relays[i].current_value' is updated but not necessarily persisted to flash instantly 
        # unless 'save_configs' is called. 
        # For now, we'll keep it in memory to avoid wearing out flash on frequent toggles.
        return found

    def get_relay_by_label(self, label):
        for relay in self.relays:
            if relay.get('label') == label:
                return relay
        return None

