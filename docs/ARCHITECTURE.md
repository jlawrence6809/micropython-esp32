# System Architecture

## Singleton Pattern

The system uses a centralized singleton pattern managed by the `InstanceManager` class in `instances.py`.

### Instance Manager

All singleton instances are accessible via the global `instances` object:

```python
from instances import instances

# Access any component
instances.config    # ConfigManager
instances.board     # BoardConfig
instances.wifi      # WiFiManager
instances.relays    # RelayManager
instances.sensors   # SensorManager
instances.rules     # RuleEngine
instances.server    # WebServer (set in main.py)
```

### Initialization Flow

1. **`boot.py`** - Runs first on every boot
   - Creates `instances` object
   - Initializes all singleton components
   - Connects to WiFi with AP fallback
   - Sets up mDNS

2. **`main.py`** - Runs after boot.py
   - Imports `instances` from `instances.py`
   - Creates WebServer with all singletons
   - Starts automation loop
   - Both use `instances.*` to access components

### Component Dependencies

```
instances
├── config (ConfigManager)
│   └── Used by: wifi, board, system_status, web_server
├── board (BoardConfig)
│   └── Used by: system_status, web_server
├── wifi (WiFiManager)
│   └── Used by: boot.py, web_server
├── relays (RelayManager)
│   └── Used by: automation_loop, web_server
├── sensors (SensorManager)
│   └── Used by: rules, automation_loop, web_server
├── rules (RuleEngine)
│   └── Used by: automation_loop
└── server (WebServer)
    └── Set in main.py, uses all other singletons
```

### Benefits

1. **Memory Efficient** - Only one instance of each component
2. **State Consistency** - No multiple instances with different states
3. **REPL Friendly** - Easy access from interactive shell
4. **Clean Dependencies** - Explicit dependency injection
5. **Easy Testing** - Can mock individual components

### REPL Usage

From the MicroPython REPL, you can interact with any component:

```python
>>> from instances import instances

# Check what's available
>>> instances
Available Instances:
  config:  ConfigManager
  board:   BoardConfig
  wifi:    WiFiManager
  relays:  RelayManager
  sensors: SensorManager
  rules:   RuleEngine
  server:  WebServer

# Get relay status
>>> instances.relays.get_relays()

# Read sensor
>>> instances.sensors.get_temperature()

# Check WiFi
>>> instances.wifi.get_ip()

# Get config
>>> instances.config.get_hostname()
```

### Adding New Components

To add a new singleton component:

1. Add property to `InstanceManager` in `instances.py`:
   ```python
   self.my_component = None  # MyComponent instance
   ```

2. Initialize in `boot.py`:
   ```python
   instances.my_component = MyComponent()
   ```

3. Use anywhere:
   ```python
   from instances import instances
   instances.my_component.do_something()
   ```

## Module Overview

### Core Modules

- **`instances.py`** - Global singleton instance manager
- **`boot.py`** - System initialization and WiFi setup
- **`main.py`** - Main application entry point
- **`config_manager.py`** - JSON-based configuration management
- **`board_config.py`** - Board-specific GPIO and pin definitions

### Hardware Control

- **`relays.py`** - Relay hardware control and state management
- **`sensors.py`** - Sensor reading and throttling

### Networking

- **`wifi_manager.py`** - WiFi connection with AP fallback
- **`web_server.py`** - HTTP server for web UI and REST API

### Automation

- **`rule_engine.py`** - Safe Python expression evaluation for rules
- **`system_status.py`** - System information collection

### Frontend

- **`preact/`** - Preact-based web UI
  - Built with `npm run build`
  - Deployed to `/www` on ESP32
  - Served by `web_server.py`

