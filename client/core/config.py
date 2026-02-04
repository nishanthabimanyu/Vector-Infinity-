import json
import os


class Config:
    def __init__(self, core=None):
        self.core = core
        self.data = {}
        self.path = "config.json"
        self.initialized = False
        
        # Default Configuration
        self.defaults = {
            # Core settings
            "version": "1.0.0",
            "theme": "dark",
            "language": "en",
            
            # LLM Defaults
            "api_key": "", # User must set this
            "model": "claude-3-5-sonnet-20241022",
            "temperature": 0.7,
            "max_tokens": 1000,
            "system_prompt": "You are Starlium, an intelligent desktop assistant.",
            
            # Starlium Modules
            "mcp_servers": [],
            "audio": {
                "input_provider": "openai_whisper",
                "output_provider": "openai_tts",
                "enabled": False
            },
            "vision": {
                "enabled": True,
                "resolution": "auto"
            },
            "presets": {
                "default": {
                    "name": "General Assistant",
                    "system_prompt": "You are a helpful assistant."
                }
            },
            "plugins": {
                "cmd_web": {"enabled": True},
                "cmd_code": {"enabled": False}
            },
            "stellarium": {
                "host": "localhost",
                "port": 8090
            }
        }

    def init(self):
        """Initialize and load config"""
        if not os.path.exists(self.path):
            self.data = self.defaults.copy()
            self.save()
        else:
            self.load()
        self.initialized = True

    def load(self):
        """Load from JSON"""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            # Merge with defaults (shallow merge for top-level keys)
            for k, v in self.defaults.items():
                if k not in self.data:
                    self.data[k] = v
        except Exception as e:
            print(f"Error loading config: {e}")
            self.data = self.defaults.copy()

    def save(self):
        """Save to JSON"""
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        """Get config value"""
        return self.data.get(key, default)

    def set(self, key, value):
        """Set config value and save"""
        self.data[key] = value
        self.save()

    def get_api_key(self):
        """Get API key (prioritizing Env Var)"""
        env_key = os.getenv("ANTHROPIC_API_KEY")
        if env_key:
            return env_key
        return self.get("api_key")
