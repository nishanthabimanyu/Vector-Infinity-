import sys
import os
import asyncio
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client.core.engine import Core
from client.controller.main import Controller
from client.core.events import KernelEvent, RenderEvent
from client.plugin.base import BasePlugin

class MockWindow:
    def __init__(self):
        self.core = None
        self.controller = None
        self.vector_client = MockVectorClient()
    
    def handle_render_event(self, event):
        print(f"[UI RENDER] {event.name}: {event.data}")

class MockVectorClient:
    async def chat(self, text):
        return f"Mock Response to: {text}"

class TestPlugin(BasePlugin):
    def handle(self, event):
        print(f"[PLUGIN] Received: {event.name} Data: {event.data}")

class TestArchitecture(unittest.IsolatedAsyncioTestCase):
    async def test_flow(self):
        print("\n--- Starting Architecture Test ---")
        
        # 1. Setup
        window = MockWindow()
        window.core = Core(window)
        window.core.init()
        
        window.controller = Controller(window)
        window.controller.setup()
        
        # 2. Register a Test Plugin
        plugin = TestPlugin(window.core)
        plugin.enabled = True
        plugin.id = "test_plugin"
        window.core.plugins.plugins["test_plugin"] = plugin
        
        # 3. Simulate User Input via Controller
        print("\n--- Action: Sending 'Hello Vector' ---")
        window.controller.chat.send("Hello Vector")
        
        # Allow async tasks to run
        await asyncio.sleep(0.1)
        
        # 4. Verify Context
        items = window.core.context.get_items()
        self.assertTrue(len(items) > 0, "Context should have items")
        last_item = items[-1]
        print(f"\n[CONTEXT CHECK] Input: '{last_item.input}' | Output: '{last_item.output}'")
        
        self.assertEqual(last_item.input, "Hello Vector")
        self.assertEqual(last_item.output, "Mock Response to: Hello Vector")
        print("\n--- Test Passed ---")

if __name__ == "__main__":
    try:
        # Run async test manually to avoid complex test runner setup in this env
        t = TestArchitecture()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(t.test_flow())
    except Exception as e:
        print(f"Test Failed: {e}")
