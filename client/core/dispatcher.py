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

    async def dispatch(self, event: BaseEvent):
        """
        Async entry point for dispatching events.
        Functions as the central nervous system.
        """
        if not isinstance(event, BaseEvent):
            print(f"[Dispatcher] Error: Invalid event type {type(event)}")
            return

        # 1. Logging (Debug)
        # print(f"[Dispatcher] Dispatching: {event.name}")

        # 2. UI Updates (Sync, usually)
        # We handle RenderEvents directly on the window/ui_controller
        if isinstance(event, RenderEvent):
            if self.window:
                self.window.handle_render_event(event)

        # 3. Kernel/Logic Routing (Async)
        # Route to appropriate controllers based on event type
        if isinstance(event, KernelEvent):
            await self._handle_kernel_event(event)
        
        # 4. Input Routing
        # handled via Kernel usually, or specialized Input controller

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
                print(f"[Dispatcher] Routing Input to VectorClient: {prompt}")
                # await self.window.vector_client.process_user_input(prompt) # Future method
