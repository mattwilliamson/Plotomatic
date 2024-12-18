from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Add role constants
ROLE_SYSTEM = "system"
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_TOOL = "tool"

class ToolCall(BaseModel):
    """Represents a tool call made by the assistant."""
    name: str = Field(..., description="Name of the function to call")
    arguments: Dict[str, Any] = Field(..., description="Arguments to pass to the function")

class Message(BaseModel):
    role: str = Field(ROLE_USER, description="Role of the message sender")
    content: str = Field("", description="Content of the message")
    show_user: Optional[bool] = Field(False, description="Whether to show the user in the UI")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp of the message")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="Tool calls made in this message")
    ephemeral: bool = False  # Flag to mark temporary messages
    allow_tool_calls: bool = True  # Flag to control whether tools can be called for this message
    interaction: Optional[Dict[str, Any]] = Field(None, description="Record of the interaction including tool calls and states")

class ChatSession(BaseModel):
    project: str = Field("", description="Project name")
    messages: List[Message] = Field(default_factory=list, description="List of messages in the chat session")
    current_interaction: Optional[Dict[str, Any]] = Field(None, description="Current interaction being processed")

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
