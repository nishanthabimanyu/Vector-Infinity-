class BasePlugin:
    def __init__(self, core=None):
        self.core = core
        self.id = "base"
        self.name = "Base Plugin"
        self.description = ""
        self.data = {}
        self.enabled = False
        self.options = {}

    def setup(self):
        """Initialize plugin options"""
        pass

    def handle(self, event):
        """
        Handle event
        :param event: BaseEvent
        """
        pass

    def add_option(self, key, type, value=None, label="", description=""):
        """Add config option"""
        self.options[key] = {
            "type": type,
            "value": value,
            "label": label,
            "description": description
        }

    def get_option(self, key):
        """Get option value"""
        if key in self.options:
            return self.options[key]["value"]
        return None

    def log(self, msg):
        """Log message"""
        print(f"[{self.id}] {msg}")
