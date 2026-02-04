from .config import Config
from .context import Context
from .plugin_manager import PluginManager
from .dispatcher import Dispatcher
from .llm import LLMService
from .mcp import MCPService
from .history import HistoryService

class Core:
    def __init__(self, window=None):
        self.window = window
        self.config = Config(self)
        self.context = Context(self)
        self.plugins = PluginManager(self)
        self.dispatcher = Dispatcher(window)
        
        # Starlium Services
        self.llm = LLMService(self)
        self.mcp = MCPService(self)
        self.history = HistoryService(self)

    def init(self):
        """Initialize all core components"""
        self.config.init()
        self.context.load()
        self.plugins.load()
        
        # Init Starlium Services
        self.llm.init()
        self.mcp.init()
        self.history.init()
        
        print("[Core] Initialized (Config, Context, Plugins, Dispatcher, LLM, MCP, History)")
