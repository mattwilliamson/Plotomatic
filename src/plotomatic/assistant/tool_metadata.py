from pydantic import BaseModel, Field
from typing import Optional

class ToolMetadata(BaseModel):
    """Metadata for assistant tools."""
    emoji: str = Field(
        default="🔧",
        description="Emoji icon representing the tool"
    )
    description: str = Field(
        default="",
        description="Description of what the tool does"
    )
    show_output: bool = Field(
        default=True,
        description="Whether to show the tool output in chat"
    )
    name: str = Field(
        description="Name of the tool function"
    )
    needs_questioning: bool = Field(
        default=False,
        description="Whether the tool output should be questioned before presenting to user"
    ) 