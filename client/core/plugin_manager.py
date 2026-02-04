import importlib
import pkgutil
import traceback

class PluginManager:
    def __init__(self, core=None):
        self.core = core
        self.plugins = {}
        self.allowed_types = ['cmd', 'camera', 'system', 'audio']

    def load(self):
        """Load all enabled plugins"""
        # Hardcoded built-in plugins for now for simplicity
        # In the future, we can scan the client/plugin directory dynamically
        
        # Example of dynamic loading logic (commented out until plugins exist):
        # self.register("cmd_web", ClientPluginWeb(self.core))
        pass

    def register(self, id, plugin):
        """Register a plugin instance"""
        try:
            plugin.core = self.core
            self.plugins[id] = plugin
            plugin.setup()
            print(f"Loaded Plugin: {id}")
        except Exception as e:
            print(f"Error registering plugin {id}: {e}")

    def dispatch(self, event, all=False):
        """Dispatch event to plugins"""
        for id, plugin in self.plugins.items():
            if plugin.enabled or all:
                try:
                    plugin.handle(event)
                except Exception as e:
                    print(f"Error in plugin {id}: {e}")
                    traceback.print_exc()

    def get(self, id):
        return self.plugins.get(id)
