#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# Vector Infinity Renderer                           #
# Handles updates to ChatOutput (QTextBrowser)       #
# ================================================== #

from PySide6.QtGui import QTextCursor
from .parser import Parser

class Renderer:
    def __init__(self, output_widget):
        """
        :param output_widget: The ChatOutput (QTextBrowser) instance to control.
        """
        self.output = output_widget
        self.parser = Parser()
        
        # CSS Style for the Chat
        self.style = """
        <style>
            body { font-family: 'Segoe UI', sans-serif; color: #e0e0e0; background-color: #0b0c10; }
            .msg-user { 
                background-color: #1f2833; 
                padding: 10px; 
                border-radius: 8px; 
                margin: 5px 0; 
                border-left: 3px solid #66fcf1;
            }
            .msg-bot { 
                background-color: #0b0c10; 
                padding: 10px; 
                border-radius: 8px; 
                margin: 5px 0;
            }
            .code-wrapper {
                background-color: #111;
                border: 1px solid #333;
                border-radius: 5px;
                margin: 10px 0;
            }
            .code-header {
                background-color: #222;
                padding: 5px 10px;
                font-size: 0.8em;
                color: #888;
                border-bottom: 1px solid #333;
            }
            pre { margin: 0; padding: 10px; color: #a3d1ff; font-family: 'JetBrains Mono', monospace; }
        </style>
        """

    def clear(self):
        self.output.clear()
        self.output.setHtml(self.style)

    def append_user_message(self, text: str):
        """
        Append a user message (Right aligned / distinct style)
        """
        html = f"<div class='msg-user'>{text}</div>"
        self._append_html(html)

    def append_bot_message(self, text: str):
        """
        Append a bot message (Markdown parsed)
        """
        parsed_html = self.parser.parse(text)
        html = f"<div class='msg-bot'>{parsed_html}</div>"
        self._append_html(html)

    def _append_html(self, html: str):
        """
        Low-level append to TextBrowser
        """
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output.setTextCursor(cursor)
        self.output.insertHtml(html)
        self.output.ensureCursorVisible()
