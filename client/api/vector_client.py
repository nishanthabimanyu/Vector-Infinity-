import asyncio
import sys
import os
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import AsyncAnthropic

class VectorClient:
    """
    The Brain of Vector Infinity. 
    Manages the MCP connection to Stellarium and the LLM via Anthropic.
    """
    def __init__(self):
        # TODO: User needs to provide Key. For now we use env or placeholder.
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "") 
        self.llm = AsyncAnthropic(api_key=self.api_key)
        self.session = None
        self.exit_stack = None
        self.tools = []
        self.is_connected = False

    async def connect(self, server_script="stellarium_mcp.py"):
        """Connects to the local Stellarium MCP Server."""
        try:
            self.exit_stack = AsyncExitStack()
            
            # Run the server script using the current python executable
            server_params = StdioServerParameters(
                command=sys.executable, 
                args=[server_script], 
                env=os.environ.copy() # Pass current env
            )
            
            # Connect Transport
            transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.session = await self.exit_stack.enter_async_context(ClientSession(transport[0], transport[1]))
            
            await self.session.initialize()
            
            # Discover capabilities
            result = await self.session.list_tools()
            self.tools = result.tools
            self.is_connected = True
            return [t.name for t in self.tools]
            
        except Exception as e:
            print(f"VECTOR CONNECT ERROR: {e}")
            self.is_connected = False
            return []

    async def chat(self, user_message, context_telemetry=None, model="claude-3-5-sonnet-latest", system_prompt_override=None):
        """
        Sends message to LLM + Context, executes MCP tools if requested.
        """
        if not self.is_connected:
            return "⚠️ Vector Core not connected to MCP Server."
            
        if not self.api_key:
            return "⚠️ Missing Anthropic API Key. Please configure it in settings."

        # 1. Prepare Context (The "System Prompt" Injection)
        system_prompt = system_prompt_override or (
            "You are Vector, an intelligent astronomy mission assistant. "
            "You have direct control over the Stellarium Observatory via MCP tools. "
            f"Current Telemetry: {context_telemetry}"
        )

        # 2. Convert MCP Tools to Anthropic format
        anthropic_tools = [{
            "name": t.name,
            "description": t.description,
            "input_schema": t.inputSchema
        } for t in self.tools]

        try:
            # 3. Call LLM
            response = await self.llm.messages.create(
                model=model,
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                tools=anthropic_tools
            )

            # 4. Handle Tool Usage (The "Action" Phase)
            final_response_text = ""
            for content in response.content:
                if content.type == 'text':
                    final_response_text += content.text
                elif content.type == 'tool_use':
                    # EXECUTE THE TOOL via MCP
                    tool_result = await self.session.call_tool(content.name, content.input)
                    res_str = tool_result.content[0].text if tool_result.content else "Done"
                    final_response_text += f"\n\n[⚡ {content.name}]: {res_str}"
            
            return final_response_text
            
        except Exception as e:
            return f"Thinking Error: {e}"
