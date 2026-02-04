import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional

class HistoryService:
    def __init__(self, core):
        self.core = core
        self.current_id = None
        self.history_dir = os.path.join(os.getcwd(), "history")
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)

    def init(self):
        """Initialize History Service"""
        print("[History] Service waiting for instructions...")
        self.new_session() # Start with a fresh session

    def new_session(self):
        """Create a new conversation session (In-Memory until first save)"""
        self.current_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Initialize in-memory state
        self.current_data = {
            "id": self.current_id,
            "created": timestamp,
            "title": "New Conversation",
            "messages": []
        }
        print(f"[History] New Session initialized: {self.current_id} (Pending Save)")
        return self.current_id

    def load(self, session_id: str) -> Dict:
        """Load a conversation by ID"""
        # Check in-memory first if it's the current one
        if self.current_id == session_id and hasattr(self, 'current_data'):
            return self.current_data

        path = os.path.join(self.history_dir, f"{session_id}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.current_id = session_id
                self.current_data = data
                return data
        return None

    def save_message(self, role: str, content: str):
        """Append a message to the current session"""
        if not self.current_id or not hasattr(self, 'current_data'):
            self.new_session()
            
        data = self.current_data
        
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        data["messages"].append(msg)
        
        # Auto-Title (Simple heuristic)
        if len(data["messages"]) == 2 and data["title"] == "New Conversation":
            # User msg is usually index 0 (if no system) or 1
            first_user = next((m for m in data["messages"] if m["role"] == "user"), None)
            if first_user:
                data["title"] = first_user["content"][:30] + "..."
        
        self.save(data)

    def save(self, data: Dict):
        """Write session data to disk"""
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)
            
        path = os.path.join(self.history_dir, f"{data['id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def delete(self, session_id: str):
        """Delete a conversation"""
        path = os.path.join(self.history_dir, f"{session_id}.json")
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"[History] Deleted session: {session_id}")
            except Exception as e:
                print(f"[History] Delete failed: {e}")
        
        # If we deleted the active session, clear in-memory or reset
        if self.current_id == session_id:
            self.current_id = None
            if hasattr(self, 'current_data'):
                del self.current_data
            self.new_session()

    def get_list(self) -> List[Dict]:
        """Get list of recent conversations"""
        items = []
        if not os.path.exists(self.history_dir):
            return []
            
        for f in os.listdir(self.history_dir):
            if f.endswith(".json"):
                path = os.path.join(self.history_dir, f)
                try:
                    # Skip if size is too small (empty/corrupt)
                    if os.path.getsize(path) < 200:
                         continue
                         
                    with open(path, "r", encoding="utf-8") as file:
                        d = json.load(file)
                        items.append({
                            "id": d.get("id"),
                            "title": d.get("title", "Untitled"),
                            "date": d.get("created", "")
                        })
                except:
                    pass
        
        # Sort by date desc
        items.sort(key=lambda x: x.get("date", ""), reverse=True)
        return items
