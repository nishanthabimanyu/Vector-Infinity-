import json
import os
import uuid
from datetime import datetime

class CtxItem:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.input = ""
        self.output = ""
        self.input_name = "User"
        self.output_name = "Vector"
        self.input_timestamp = 0
        self.output_timestamp = 0
        self.urls = []
        self.images = []
        self.files = []
        self.extra = {}

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(data):
        item = CtxItem()
        item.__dict__.update(data)
        return item

class Context:
    def __init__(self, core=None):
        self.core = core
        self.items = []
        self.current_id = "default"
        self.path = "history.json"

    def add(self, item: CtxItem):
        """Add item to current context"""
        self.items.append(item)
        self.save()

    def get_items(self):
        """Get all items"""
        return self.items

    def clear(self):
        """Clear context"""
        self.items = []
        self.save()

    def load(self):
        """Load history"""
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.items = [CtxItem.from_dict(x) for x in data.get("items", [])]
        except Exception as e:
            print(f"Error loading context: {e}")

    def save(self):
        """Save history"""
        try:
            data = {
                "items": [item.to_dict() for item in self.items]
            }
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving context: {e}")
