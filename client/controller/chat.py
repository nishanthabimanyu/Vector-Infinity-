from client.core.events import KernelEvent, RenderEvent, InputEvent
from client.core.context import CtxItem
import asyncio

class ChatController:
    def __init__(self, window=None):
        self.window = window

    def setup(self):
        """Setup chat connection"""
        pass

    def send(self, text):
        """
        Handle user input
        :param text: input text
        """
        # 1. Dispatch Input Event (Plugins can modify this)
        event = KernelEvent(KernelEvent.INPUT_USER, {"value": text})
        self.window.core.dispatcher.dispatch(event)
        
        # 2. Render User Message
        self.window.core.dispatcher.dispatch(RenderEvent(RenderEvent.APPEND_TEXT, {
            "text": f"**User**: {text}\n",
            "type": "input"
        }))

        # [Starlium] Save to History
        if self.window.core.history:
            self.window.core.history.save_message("user", text)

        # 3. Add to Context
        ctx_item = CtxItem()
        ctx_item.input = text
        self.window.core.context.add(ctx_item)
        
        # 4. Async Process (Run via qasync/asyncio)
        if hasattr(self.window, 'vector_client'):
            asyncio.create_task(self.process_response(text, ctx_item))

    async def process_response(self, text, ctx_item):
        """Process AI response with Starlium Agentic Loop"""
        # Notify Busy
        self.window.core.dispatcher.dispatch(KernelEvent(KernelEvent.STATE_BUSY))

        try:
            # 1. Prepare Core Services
            core = self.window.core
            messages = [{"role": "user", "content": text}]
            
            # 2. Get Tools from MCP
            tools = core.mcp.get_all_tools()
            
            # 3. Agent Loop (Max 5 turns)
            final_response = ""
            for turn in range(5):
                # Call LLM
                response_msg = core.llm.chat(messages, tools=tools, stream=False)
                
                # Check outcome
                content_blocks = response_msg.content
                has_tool_use = False
                
                for block in content_blocks:
                    if block.type == "text":
                        final_response += block.text
                    elif block.type == "tool_use":
                        has_tool_use = True
                        tool_name = block.name
                        tool_args = block.input
                        tool_id = block.id
                        
                        # Notify UI of Action
                        self.window.core.dispatcher.dispatch(RenderEvent(RenderEvent.APPEND_TEXT, {
                            "text": f"\n\n> ⚙️ **Executing**: `{tool_name}` ...\n",
                            "type": "output"
                        }))
                        
                        # Execute MCP Tool
                        result = core.mcp.call_tool(tool_name, tool_args)
                        
                        # Append result to history for next turn
                        messages.append({"role": "assistant", "content": content_blocks})
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": str(result)
                            }]
                        })
                
                if not has_tool_use:
                    break
            
            # Update Context
            ctx_item.output = final_response
            self.window.core.context.save()

            # [Starlium] Save to History
            if self.window.core.history:
                self.window.core.history.save_message("assistant", final_response)

            # Render Output
            self.window.core.dispatcher.dispatch(RenderEvent(RenderEvent.APPEND_TEXT, {
                "text": final_response, # Markdown renderer will handle format
                "type": "output"
            }))

        except Exception as e:
            self.window.core.dispatcher.dispatch(RenderEvent(RenderEvent.APPEND_TEXT, {
                "text": f"**Error**: {str(e)}",
                "type": "error"
            }))
        
        # Notify Idle
        self.window.core.dispatcher.dispatch(KernelEvent(KernelEvent.STATE_IDLE))
