import requests
import json
from typing import List, Dict, Any, Optional

class GeminiProvider:
    def __init__(self, api_key: str, model_id: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def chat(self, messages: List[Dict], tools: Optional[List[Dict]] = None, system_prompt: str = None) -> Any:
        """
        Send chat request to Gemini via REST API
        """
        url = f"{self.base_url}/{self.model_id}:generateContent?key={self.api_key}"
        
        # 1. Build Payload
        contents = []
        
        # Map Roles
        # Starlium: user, assistant
        # Gemini: user, model
        
        # We need to merge system prompt if possible, or send as system_instruction (for 1.5)
        payload = {
            "contents": [],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024
            }
        }

        # System Instruction (Only supported on 1.5+ models via specific field)
        if system_prompt:
             payload["systemInstruction"] = {
                 "parts": [{"text": system_prompt}]
             }

        # Convert Messages
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": m["content"]}]
            })
            
        payload["contents"] = contents

        # 2. Add Tools (Placeholder for future)
        # if tools: ...

        # 3. Request
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"Gemini API Error {response.status_code}: {response.text}")
                
            data = response.json()
            
            # 4. Parse Response
            # Structure: {"candidates": [{"content": {"parts": [{"text": "..."}]}}]}
            candidates = data.get("candidates", [])
            if not candidates:
                 # Check for safety block
                 prompt_feedback = data.get("promptFeedback", {})
                 if "blockReason" in prompt_feedback:
                     return self._mock_response(f"[Blocked] {prompt_feedback['blockReason']}")
                 return self._mock_response("[No response generated]")
                 
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return self._mock_response(text)
            
        except Exception as e:
            raise Exception(f"Gemini Request Failed: {str(e)}")

    def _mock_response(self, text):
         class MockBlock:
             def __init__(self, t):
                 self.type = "text"
                 self.text = t
                 
         class MockResponse:
             def __init__(self, t):
                 self.content = [MockBlock(t)]
         
         return MockResponse(text)
