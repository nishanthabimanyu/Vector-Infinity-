#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# Vector Infinity Async Dispatcher                   #
# Bridges Sync UI Events with Async Business Logic   #
# ================================================== #

import asyncio
from typing import List, Tuple
from .events import BaseEvent, KernelEvent, RenderEvent

class Dispatcher:
    def __init__(self, window=None):
        """
        Initialize Dispatcher.
        :param window: Reference to the MainWindow (or LogicGate) for UI updates.
        """
        self.window = window

    def dispatch(self, event: BaseEvent):
        """
        Sync entry point for dispatching events.
        Functions as the central nervous system.
        """
        if not isinstance(event, BaseEvent):
            print(f"[Dispatcher] Error: Invalid event type {type(event)}")
            return

        # 1. Logging (Debug)
        # print(f"[Dispatcher] Dispatching: {event.name}")

        # 2. UI Updates (Sync)
        # We handle RenderEvents directly on the window/ui_controller
        if isinstance(event, RenderEvent):
            if self.window:
                self.window.handle_render_event(event)

        # 3. Kernel/Logic Routing (Async Scheduled)
        # Route to appropriate controllers based on event type
        if isinstance(event, KernelEvent):
            # Schedule async processing
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._handle_kernel_event(event))
            except RuntimeError:
                # No loop running (e.g. during sync tests), run sync or ignore
                pass
        
        # 4. Plugin Routing
        # Dispatch to all enabled plugins
        if hasattr(self.window, 'core') and self.window.core:
             self.window.core.plugins.dispatch(event)

    async def _handle_kernel_event(self, event: KernelEvent):
        """
        Route kernel logic events to the VectorClient or specific Workers.
        """
        # In the future, this will route to self.window.controllers.mcp, etc.
        # For now, we hook into the existing vector_client if available
        if hasattr(self.window, 'vector_client') and self.window.vector_client:
            if event.name == KernelEvent.INPUT_USER:
                # Example: Pass to MCP
                prompt = event.data.get('value', '')
                # print(f"[Dispatcher] Routing Input to VectorClient: {prompt}")
                # await self.window.vector_client.process_user_input(prompt) # Future method
