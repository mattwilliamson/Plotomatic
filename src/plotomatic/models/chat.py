from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ToolCall(BaseModel):
    """Represents a tool call made by the assistant."""
    function: Dict[str, Any] = Field(..., description="Function details including name and arguments")

class Message(BaseModel):
    role: str = Field("", description="Role of the message sender")
    content: str = Field("", description="Content of the message")
    show_user: Optional[bool] = Field(False, description="Whether to show the user in the UI")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp of the message")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="Tool calls made in this message")

class ChatSession(BaseModel):
    project: str = Field("", description="Project name")
    messages: List[Message] = Field(default_factory=list, description="List of messages in the chat session")

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
