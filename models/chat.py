from datetime import datetime
from typing import List
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: str
    content: str
    show_user: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatSession(BaseModel):
    project: str
    messages: List[Message] = []

    @classmethod
    def load_from_file(cls, path):
        if path.exists():
            with open(path, 'r') as f:
                data = cls.model_validate_json(f.read())
            return data
        return None

    def save_to_file(self, path):
        with open(path, 'w') as f:
            f.write(self.model_dump_json(indent=4))
