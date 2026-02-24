#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# Vector Infinity Cultural Hub View                  #
# Hosts the interactive card-based cultural database #
# ================================================== #

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Signal, QObject, Slot
from PySide6.QtWebChannel import QWebChannel
import os
import json
import requests
from client.logic.conversions import convert_to_cultural

class CulturalBridge(QObject):
    """
    Bridge class to handle requests from the Cultural Hub JS.
    Routes API calls via Python to avoid CORS/Fetch errors in the browser.
    """
    def __init__(self):
        super().__init__()
        self.session = requests.Session()

    @Slot(str, str)
    def set_property(self, prop_id, value):
        try:
            url = "http://localhost:8090/api/stelproperty/set"
            self.session.post(url, data={'id': prop_id, 'value': value}, timeout=2)
        except Exception as e:
            print(f"Bridge set_property error: {e}")

    @Slot(str, float, float, float)
    def set_location(self, name, lat, lon, elev):
        try:
            url = "http://localhost:8090/api/location/set"
            self.session.post(url, data={
                'name': name, 'latitude': lat, 'longitude': lon, 'altitude': elev
            }, timeout=2)
        except Exception as e:
            print(f"Bridge set_location error: {e}")

class CulturalHubView(QWidget):
    """
    A PySide6 view that hosts the Cultural Hub HTML interface.
    This provides a high-fidelity 'card game' aesthetic for exploring cultures.
    """
    request_view_change = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QWebEngineView()
        
        # Set up QWebChannel bridge
        self.bridge = CulturalBridge()
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)
        
        # Determine the path to the HTML file
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(curr_dir, "..", "ui", "cultural_hub.html")
        
        if os.path.exists(html_path):
            self.browser.setUrl(QUrl.fromLocalFile(html_path))
        else:
            # Fallback or error handling
            print(f"Error: Cultural Hub HTML not found at {html_path}")
            self.browser.setHtml("<h1>Error: Cultural Hub UI missing.</h1>")

        self.layout.addWidget(self.browser)

    def update_telemetry(self, telemetry):
        """
        Receives raw telemetry from Stellarium and pushes converted
        cultural coordinates to the JS interface.
        """
        ra = telemetry.get('ra', 0.0)
        dec = telemetry.get('dec', 0.0)
        az = telemetry.get('az', 0.0)
        alt = telemetry.get('alt', 0.0)
        jday = telemetry.get('jday', 2451545.0)

        # Generate conversions for all registered cultures
        mapping = {
            "BAB": "babylonian",
            "SUR": "indian",
            "MAY": "maya",
            "PTO": "western",
            "CHI": "chinese",
            "ISL": "arabic"
        }
        
        conversions = {}
        for short_id, culture_key in mapping.items():
            conversions[short_id] = convert_to_cultural(ra, dec, az, alt, jday, culture_key)

        # Push to JS
        js_code = f"if (window.updateConversions) window.updateConversions({json.dumps(conversions)});"
        self.browser.page().runJavaScript(js_code)

    def reload_hub(self):
        """Reloads the hub content."""
        self.browser.reload()
