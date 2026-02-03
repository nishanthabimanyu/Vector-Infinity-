#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# Vector Infinity Core Events                        #
# Adapted from py-gpt for Async/Qt Hybrid            #
# ================================================== #

class BaseEvent:
    def __init__(self, name: str, data: dict = None):
        self.name = name
        self.data = data if data else {}
        self.stop = False  # If True, propagation stops
        self.ctx = None    # Context reference

    def __str__(self):
        return f"{self.name} (Data: {self.data})"

class KernelEvent(BaseEvent):
    # System states
    STATE_IDLE = "state.idle"
    STATE_BUSY = "state.busy"
    STATE_ERROR = "state.error"
    
    # Logic
    INPUT_USER = "input.user"       # Raw user input provided
    REQUEST_TELEM = "request.telem" # Request telemetry update

class RenderEvent(BaseEvent):
    # UI Updates
    CLEAR_OUTPUT = "render.clear_output"
    APPEND_TEXT = "render.append_text"
    APPEND_HTML = "render.append_html"
    UPDATE_STATUS = "render.update_status"
    
    # Custom Vector Events
    UPDATE_TELEM = "render.update_telem" # Specific for telemetry cards

class InputEvent(BaseEvent):
    # User Interactions
    INPUT_SENT = "input.sent"
    INPUT_STOP = "input.stop"
