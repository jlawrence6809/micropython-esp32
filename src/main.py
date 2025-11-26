# main.py - MicroPython Automation Platform
# This file runs automatically after boot.py

import uasyncio as asyncio
from instances import instances
import sys

async def automation_loop():
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
            instances.sensors.update_all()
            
            # Get current relay configurations
            relay_config = instances.relays.get_relays()
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
                    result = instances.rules.evaluate_safe(rule, default=relay.get('value', False))
                    
                    # Update relay state if changed
                    if result != relay.get('value'):
                        print(f"Rule for '{label}': {rule} -> {result}")
                        # Set relay state, keeping auto mode enabled
                        instances.relays.set_relay_by_label(label, result, keep_auto=True)
                    
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
    
    # Start Web Server (already initialized in instances)
    asyncio.create_task(instances.server.start())
    
    # Start Automation Loop
    asyncio.create_task(automation_loop())
    
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
