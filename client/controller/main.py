from .chat import ChatController

class Controller:
    def __init__(self, window=None):
        self.window = window
        self.chat = ChatController(window)

    def setup(self):
        """Setup all controllers"""
        self.chat.setup()
        print("[Controller] Setup Complete")

    def init(self):
        """Initialize data"""
        pass
