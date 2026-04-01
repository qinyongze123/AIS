import json
import os

class GlobalVariables:
    """
    Global variable file for centralized read/write operations.
    Handles settings, configurations, and shared runtime states.
    """
    def __init__(self, config_path: str = "config.json"):
        # Initial setting of constants or loading defaults
        self.config_path = config_path
        self._settings = {
            "ROBOT_IP": "192.168.1.10",
            "INJECTOR_PORT": "/dev/ttyUSB0",
            "DETECTOR_THRESHOLD": 0.85,
            "LOG_DIR": "log/",
            "DEFAULT_VELOCITY": 5.0,
            "REFRESH_RATE_MS": 100,
            "INJECT_ANGLE": 30.0,
            
            "LIMIT_X": 100.0,
            "LIMIT_Y": 50.0,
            "LIMIT_Z": 150.0,
        }
        # Load external configuration if it exists
        self.load_from_disk()

    def load_from_disk(self):
        # Load from JSON or YAML if exists
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._settings.update(json.load(f))

    def save_to_disk(self):
        # Persistent storage of current configuration
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._settings, f, indent=4)

    def get_setting(self, key: str, default=None):
        # Access thread-safe configuration settings
        return self._settings.get(key, default)

    def set_setting(self, key: str, value):
        # Update thread-safe configuration settings
        self._settings[key] = value

# Singleton instance for easy access across modules
session_globals = GlobalVariables()
