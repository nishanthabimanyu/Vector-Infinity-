#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# Vector Infinity Lab Dashboard                      #
# Research Lab View for Deep Space Analysis          #
# ================================================== #

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QFrame)
from PySide6.QtCore import Signal, Qt
from PySide6.QtWebEngineWidgets import QWebEngineView

class LabDashboard(QWidget):
    request_sidebar = Signal()
    request_view_change = Signal(int) # Signal to request switching views

    def __init__(self, vector_client=None, parent=None):
        super().__init__(parent)
        self.vector_client = vector_client
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header / Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #0b0c10; border-bottom: 1px solid #1f2833;")
        toolbar.setFixedHeight(50)
        
        tb_layout = QHBoxLayout(toolbar)
        
        # Sidebar Toggle
        self.btn_menu = QPushButton("☰")
        self.btn_menu.setFixedSize(40, 30)
        self.btn_menu.clicked.connect(self.request_sidebar.emit)
        self.btn_menu.setStyleSheet("""
            QPushButton { background: transparent; color: #66fcf1; font-size: 18px; border: none; }
            QPushButton:hover { color: white; }
        """)
        tb_layout.addWidget(self.btn_menu)
        
        title = QLabel("RESEARCH LAB > CHROMIUM ENGINE")
        title.setStyleSheet("color: #c5c6c7; font-weight: bold; letter-spacing: 1px;")
        tb_layout.addWidget(title)
        
        tb_layout.addStretch()

        # Orbital Scanner Link
        self.btn_orbital = QPushButton("ORBITAL SCANNER")
        self.btn_orbital.setCursor(Qt.PointingHandCursor)
        self.btn_orbital.setStyleSheet("""
            QPushButton {
                background: rgba(102, 252, 241, 0.1); 
                border: 1px solid #66fcf1; 
                color: #66fcf1; 
                font-size: 10px; font-weight: bold; 
                padding: 6px 12px; border-radius: 3px;
            }
            QPushButton:hover { background: #66fcf1; color: black; }
        """)
        self.btn_orbital.clicked.connect(lambda: self.request_view_change.emit(5))
        tb_layout.addWidget(self.btn_orbital)
        
        layout.addWidget(toolbar)
        
        # Web View (Chromium)
        self.browser = QWebEngineView()
        self.browser.setStyleSheet("background-color: #000;")
        # Use a local placeholder to avoid preload warnings and memory overhead
        self.browser.setUrl(r"file:///d:/Vector%20Infinity/client/ui/placeholder.html")
        
        layout.addWidget(self.browser)
