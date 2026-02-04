import anthropic
from typing import List, Dict, Any, Optional
# [Starlium] Providers
from .llm_providers.gemini import GeminiProvider

class LLMService:
    def __init__(self, core):
        self.core = core
        self.client = None
        self.provider_type = "anthropic" # anthropic, gemini
        self.model = "gemini-1.5-flash" # Default to free model for now
        self.api_key = ""

    def init(self):
        """Initialize LLM Provider based on Config"""
        self.api_key = self.core.config.get("api_key")
        self.model = self.core.config.get("model", "gemini-1.5-flash")
        
        print(f"[LLM] Init triggered. Model: {self.model}, Key Present: {bool(self.api_key)}") # DEBUG
        
        if not self.api_key:
            print("[LLM] No API Key found. Service pending.")
            return

        if self.model.startswith("gemini"):
            self.provider_type = "gemini"
            try:
                self.client = GeminiProvider(api_key=self.api_key, model_id=self.model)
                print(f"[LLM] Gemini Service initialized: {self.model}")
            except Exception as e:
                print(f"[LLM] Gemini Init Error: {e}")
        else:
            self.provider_type = "anthropic"
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                print(f"[LLM] Anthropic Service initialized: {self.model}")
            except Exception as e:
                print(f"[LLM] Anthropic Init Error: {e}")

    def set_model(self, model_id: str):
        """Switch current model"""
        self.model = model_id
        self.core.config.set("model", model_id)
        # Re-init if provider might change (e.g. going from claude to gemini)
        self.init()

    def chat(self, messages: List[Dict], tools: Optional[List[Dict]] = None, stream: bool = True):
        """
        Send chat request to Provider
        """
        # Auto-init if missing
        if not self.client:
            self.init()
        
        # Check again
        if not self.client:
            raise Exception("❌ API Key Missing. Please Copy your Key from Google AI Studio -> Go to Settings (Gear) -> Link Tab -> Paste API Key.")

        # Prepare system prompt
        system_prompt = self.core.config.get("system_prompt", "")
        if not system_prompt: system_prompt = "You are Starlium, a helpful AI assistant."

        if self.provider_type == "gemini":
            # Gemini Provider handles its own wrapping
            try:
                return self.client.chat(messages, tools, system_prompt=system_prompt)
            except Exception as e:
                # Catch-all to provide cleaner UI error
                raise Exception(f"Gemini API Error: {str(e)}")
        
        
        else:
            # Anthropic Logic
            kwargs = {
                "model": self.model,
                "max_tokens": self.core.config.get("max_tokens", 1024),
                "temperature": self.core.config.get("temperature", 0.7),
                "system": system_prompt,
                "messages": messages
            }

            if tools:
                kwargs["tools"] = tools

            try:
                # Force non-stream for now to unify interface or handle stream
                # If existing code expects stream, we need to adapt Gemini accordingly
                # For safety, let's verify if ChatController expects full response or stream
                # ChatController.process_response calls await self.window.vector_client.chat
                # Old vector_client.chat returned full response text.
                # So we should return full object or text.
                # Anthropic client returns Message object.
                
                return self.client.messages.create(stream=stream, **kwargs)
            except Exception as e:
                print(f"[LLM] Error: {e}")
                raise e

    def get_models(self) -> List[str]:
        """Return available models"""
        return [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229"
        ]
