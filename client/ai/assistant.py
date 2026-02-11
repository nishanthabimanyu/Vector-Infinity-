"""
AI Assistant for Stellarium Control using Gemini API
Provides natural language interface to Stellarium via direct HTTP API
"""

import os
import requests
import google.generativeai as genai

class StellariumAI:
    """AI Assistant for natural language Stellarium control"""
    
    def __init__(self, stellarium_host="localhost", stellarium_port=8090):
        """
        Initialize AI assistant with Stellarium connection
        
        Args:
            stellarium_host: Stellarium server host (default: localhost)
            stellarium_port: Stellarium Remote Control API port (default: 8090)
        """
        self.base_url = f"http://{stellarium_host}:{stellarium_port}"
        
        # Configure Gemini API
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        
        # Initialize Gemini model with automatic function calling
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash-exp',
            tools=[self.slew_to_target, self.set_fov, self.set_time, self.get_object_info, self.set_location],
            system_instruction="""You are an astronomy assistant integrated with Stellarium planetarium software.

You can help users explore the night sky by controlling Stellarium through function calls.
Be concise, friendly, and educational. When users ask to see objects, use the slew_to_target function.
Provide interesting facts about celestial objects when appropriate.

Always confirm actions you take (e.g., "I've pointed the telescope at Mars").
If something goes wrong, explain the error clearly."""
        )
        
        # Start chat session
        self.chat = self.model.start_chat(enable_automatic_function_calling=True)
        
    def slew_to_target(self, target: str, mode: str = "center"):
        """Point telescope at celestial object"""
        try:
            # Search for object first
            search_url = f"{self.base_url}/api/objects/find?str={target}"
            resp = requests.get(search_url, timeout=5)
            
            if resp.status_code == 200:
                # Select object
                select_url = f"{self.base_url}/api/main/focus"
                params = {"target": target}
                requests.post(select_url, json=params, timeout=5)
                
                if mode == "zoom":
                    # Set 5° FOV for zoom
                    fov_url = f"{self.base_url}/api/main/fov"
                    requests.post(fov_url, json={"fov": 5.0}, timeout=5)
                
                return f"✅ Pointed telescope at {target}"
            else:
                return f"❌ Could not find object: {target}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def set_fov(self, fov_degrees: float):
        """Set field of view (zoom level)"""
        try:
            url = f"{self.base_url}/api/main/fov"
            resp = requests.post(url, json={"fov": fov_degrees}, timeout=5)
            if resp.status_code == 200:
                return f"✅ Set FOV to {fov_degrees}°"
            return f"❌ Failed to set FOV"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def set_time(self, datetime_str: str):
        """Change simulation time"""
        try:
            url = f"{self.base_url}/api/main/time"
            
            # Handle special keywords
            if datetime_str.lower() == "now":
                resp = requests.post(url, json={"time": "now"}, timeout=5)
            else:
                resp = requests.post(url, json={"time": datetime_str}, timeout=5)
            
            if resp.status_code == 200:
                return f"✅ Set time to {datetime_str}"
            return f"❌ Failed to set time"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def get_object_info(self, object_name: str):
        """Get information about celestial object"""
        try:
            url = f"{self.base_url}/api/objects/info?name={object_name}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return f"Object: {object_name}\\nRA: {data.get('ra', 'N/A')}\\nDec: {data.get('dec', 'N/A')}\\nAlt: {data.get('altitude', 'N/A')}°"
            return f"❌ Object not found: {object_name}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def set_location(self, latitude: float, longitude: float, name: str = "Custom"):
        """Change observer location"""
        try:
            url = f"{self.base_url}/api/location/setlocationfields"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "name": name
            }
            resp = requests.post(url, json=params, timeout=5)
            if resp.status_code == 200:
                return f"✅ Location set to {name} ({latitude}, {longitude})"
            return f"❌ Failed to set location"
        except Exception as e:
            return f"❌ Error: {str(e)}"
        
    def send_message(self, user_message):
        """
        Send a message to the AI and get response with automatic function calling
        
        Args:
            user_message: User's natural language input
            
        Returns:
            str: AI's response text
        """
        try:
            response = self.chat.send_message(user_message)
            return response.text
            
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def reset_conversation(self):
        """Reset the chat history"""
        self.chat = self.model.start_chat(enable_automatic_function_calling=True)
        return "✅ Conversation reset"
