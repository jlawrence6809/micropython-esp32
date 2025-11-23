# main.py - MicroPython Automation Platform
# This file runs automatically after boot.py

import uasyncio as asyncio
from web_server import WebServer
from sensors import SensorManager
from rule_engine import RuleEngine
from relays import RelayManager
import sys

async def automation_loop(sensors, rule_engine, relays):
    """Main automation loop - evaluates rules and updates relay states.
    
    Runs every 1 second:
    1. Update sensor readings (with throttling)
    2. Evaluate rules for each relay in auto mode
    3. Apply physical relay states
    """
    print("Starting automation loop...")
    
    while True:
        try:
            # Update all sensors (throttled internally)
            sensors.update_all()
            
            # Get current relay configurations
            relay_config = relays.get_relays()
            relay_list = relay_config.get('relays', [])
            
            # Evaluate rules for each relay in auto mode
            for relay in relay_list:
                if not relay.get('auto', False):
                    # Manual mode - skip rule evaluation
                    continue
                
                rule = relay.get('rule', '')
                if not rule or rule == '["NOP"]':
                    # No rule or NOP rule - keep current state
                    continue
                
                label = relay.get('label', 'Unknown')
                
                try:
                    # Evaluate the rule
                    result = rule_engine.evaluate_safe(rule, default=relay.get('value', False))

                    print("--------------------------------")
                    print(f"Relay: {relay}")
                    print(f"Rule: {rule}")
                    print(f"Rule result: {result}")
                    
                    # Update relay state if changed
                    if result != relay.get('value'):
                        print(f"Rule for '{label}': {rule} -> {result}")
                        # Set relay state, keeping auto mode enabled
                        relays.set_relay_by_label(label, result, keep_auto=True)
                    print(f"New relay state: {relays.get_relay_by_label(label)}")
                    
                except Exception as e:
                    print(f"Error evaluating rule for '{label}': {e}")
                    # Keep current state on error
            
        except Exception as e:
            print(f"Error in automation loop: {e}")
            import sys
            sys.print_exception(e)
        
        # Run every 1 second
        await asyncio.sleep(1)

async def main():
    print("Starting main.py...")
    
    # Initialize subsystems
    sensors = SensorManager()
    rule_engine = RuleEngine(sensors)
    relays = RelayManager()
    
    # Start Web Server (pass sensors and relays to share instances)
    server = WebServer(sensors=sensors, relays=relays)
    asyncio.create_task(server.start())
    
    # Start Automation Loop
    asyncio.create_task(automation_loop(sensors, rule_engine, relays))
    
    print("System started!")
    
    # Main loop
    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped by user")
        # Clean exit (allows REPL to take over without hard crash state if desired)
        sys.exit(0)
    except Exception as e:
        print(f"Error in main: {e}")
