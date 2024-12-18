# assistant/story_overview_assistant.py

from .base_assistant import BaseChatAssistant
from .states import AssistantState
from plotomatic.models.story import Story
from plotomatic.models.chat import Message, ROLE_SYSTEM, ROLE_USER, ROLE_ASSISTANT, ROLE_TOOL
from pathlib import Path
import json
from datetime import datetime
from typing import List, Optional

# TODO: Look through the latest messages to see if we have any information to add to secret_knowledge or 
# requirements

class StoryOverviewAssistant(BaseChatAssistant):
    """
    The primary assistant responsible for orchestrating the story overview development process.
    This assistant directly communicates with users to gather high-level story details
    (e.g., title, genre, plot_overview, etc.) and manages the conversation flow.
    
    The assistant collects requirements, asks questions, and delegates creative writing
    tasks to specialized tools when needed. However, it maintains direct dialogue with
    the user throughout the process.
    """

    MODEL = "llama3.3"  # Override the model at the class level

    # Fields to skip when processing story state
    SKIP_FIELDS = {
        'acts',              # Handled in separate assistant
        'characters',        # Handled in separate assistant
        'props',            # Handled in separate assistant
        'cover_design',      # Complex object
        '_story_dialogue',   # Internal state
        'author_email',      # Optional field
        'secret_knowledge',  # Optional field
    }

    # A system prompt specialized for story overview
    STORY_OVERVIEW_SYSTEM_PROMPT = """Your role is to actively engage with users, ask questions, and guide them through defining the fundamental elements of their story.

You should:
1. Maintain direct dialogue with the user throughout the process
2. Ask specific questions to gather story requirements
3. Answer questions directly when you can - only use creative_write for generating new creative content
4. Always explain your suggestions and ask for user approval before making changes
5. Help users refine their ideas through conversation

When to use tools:
- creative_write: ONLY use this when you need to generate new creative content like plot ideas or descriptions
- set_property: ONLY use after:
  * Getting explicit user approval
  * Having complete information for the property
  * Verifying it's a valid property (title, genre, plot_overview, etc.)
- For simple questions, greetings, or clarifications, just respond directly without using tools
- If tool output has enough information to set any properties, then set those properties

For new conversations:
- Introduce yourself and explain how you can help
- Ask what kind of story they want to create
- Don't try to set properties until you have gathered relevant information

Current Story State:
{story_state}

Empty Fields That Need Attention:
{empty_fields}

Important Rules:
- You are the primary communicator with the user - maintain an engaging conversation
- Ask clarifying questions when needed instead of making assumptions
- Don't call set_property without explicit user approval and complete information
- Only call set_property if the new value is different from the old value
- If set_property is dependent on a previous creative_write, then you must call creative_write first
- For simple interactions like greetings or questions about the process, respond directly without using tools
- The author field should not be made up unless the user explicitly asks for it
- Any time you have information that can be used to set a property, you should set that property, whether from a tool call or user input
- Any time you see any hard requirements from the user, append it to the requirements field. Be sure to include all current requirements as well. An example of a hard requirement is no explicit content or no violence or a specific character is requested.
"""

    @classmethod
    def load_for_project(cls, 
                        project_path: Path,
                        agent_temperature: Optional[float] = None,
                        creative_temperature: Optional[float] = None,
                        agent_seed: Optional[int] = None,
                        creative_seed: Optional[int] = None) -> 'StoryOverviewAssistant':
        """Factory method to load or create an assistant for a specific project"""
        assistant_state_path = project_path / "story_overview_state.json"
        
        assistant = cls(
            storage_path=str(assistant_state_path),
            agent_temperature=agent_temperature,
            creative_temperature=creative_temperature,
            agent_seed=agent_seed,
            creative_seed=creative_seed
        )
        
        return assistant

    def __init__(self, 
                 storage_path="story_overview_state.json",
                 agent_temperature: Optional[float] = None,
                 creative_temperature: Optional[float] = None,
                 agent_seed: Optional[int] = None,
                 creative_seed: Optional[int] = None):
        """Initialize the StoryOverviewAssistant.
        
        Args:
            storage_path (str): Path to save assistant state
            agent_temperature (Optional[float]): Temperature for main LLM responses
            creative_temperature (Optional[float]): Temperature for creative writing
            agent_seed (Optional[int]): Seed for main LLM responses
            creative_seed (Optional[int]): Seed for creative writing
        """
        super().__init__(
            storage_path=storage_path,
            system_prompt=self.BASE_SYSTEM_PROMPT,
            agent_temperature=agent_temperature,
            creative_temperature=creative_temperature,
            agent_seed=agent_seed,
            creative_seed=creative_seed
        )
        self.story = Story()  # Will be set from outside
        
        # Enable only the tools we want for story overview
        self.available_tools = {}  # Clear all tools first
        self.register_tool('set_property')  # Enable built-in set_property
        self.register_tool('creative_write')  # Enable built-in creative_write

    def add_ephemeral_message(self, role: str, content: str, allow_tool_calls: bool = True):
        """
        Add a message that will be sent to the LLM but not saved in chat history.
        
        Args:
            role (str): The role of the message sender ("system", "user", or "assistant")
            content (str): The message content
            allow_tool_calls (bool): Whether to allow tool calls for this message
        """
        super().add_ephemeral_message(role, content, allow_tool_calls)

    def all_fields_filled(self) -> bool:
        """
        Check if the minimal required fields (title, genre, plot_overview, etc.) are filled.
        """
        required_fields = ["title", "genre", "plot_overview"]
        for f in required_fields:
            if not getattr(self.story, f, None):
                return False
        return True

    def get_empty_fields(self) -> list[str]:
        """
        Get all empty required fields from the story object.
        Returns a list of field names.
        """
        if self.story is None:
            return []
        
        empty_fields = []
        
        # Get all fields from the Story model
        for field_name, field in self.story.model_fields.items():
            if field_name in self.SKIP_FIELDS:
                continue
                
            value = getattr(self.story, field_name)
            # Check if field is empty (None, empty string, or empty list)
            if value is None or value == "" or (isinstance(value, list) and len(value) == 0):
                empty_fields.append(field_name)
                
        return empty_fields

    def _format_story_state(self) -> str:
        """Format the current story state for the system prompt."""
        if self.story is None:
            return "No story loaded yet"
        
        lines = ["Current Values:"]
        field_descriptions = ["Field Descriptions:"]
        
        for field_name, field in self.story.model_fields.items():
            if field_name in self.SKIP_FIELDS:
                continue
                
            # Add the field value
            value = getattr(self.story, field_name)
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value) if value else "[]"
            lines.append(f"{field_name}: {value}")
            
            # Add the field description
            field_descriptions.append(f"{field_name}: {field.description}")
        
        return "\n".join(field_descriptions) + "\n\n" + "\n".join(lines)

    def _format_empty_fields(self, empty_fields: list[str]) -> str:
        """Format the empty fields for the system prompt."""
        if not empty_fields:
            return "All required fields have been filled."
        
        return "\n".join([
            f"- {field_name}"
            for field_name in empty_fields
        ])

    def initialize_prepended_messages(self):
        """Override to set up our specialized system prompts."""
        formatted_prompt = self.STORY_OVERVIEW_SYSTEM_PROMPT.format(
            story_state="No story loaded yet",
            empty_fields="Story not initialized"
        )
        
        self.prepended_messages = [
            Message(
                role=ROLE_SYSTEM,
                content=self.BASE_SYSTEM_PROMPT,
                allow_tool_calls=True
            ),
            Message(
                role=ROLE_SYSTEM,
                content=formatted_prompt,
                allow_tool_calls=True
            )
        ]

    def get_prepended_messages(self) -> List[Message]:
        """Get the current prepended messages with updated story state."""
        # Only update the story state if we have a story object
        if self.story is not None:
            empty_fields = self.get_empty_fields()
            formatted_prompt = self.STORY_OVERVIEW_SYSTEM_PROMPT.format(
                story_state=self._format_story_state(),
                empty_fields=self._format_empty_fields(empty_fields)
            )
            
            # Update the second message (story overview prompt)
            self.prepended_messages[1].content = formatted_prompt
        
        return self.prepended_messages

    def run(self):
        """Override run to handle first-time setup and cleanup."""
        # If this is the first run and no messages exist, add initial message
        if not self.chat_session.messages and self.state == self.STATE_GENERATING_OUTPUT:
            # Add the greeting as an ephemeral message
            self.add_ephemeral_message(
                role="user",
                content="",
                allow_tool_calls=False
            )

        # Run normal assistant logic
        super().run()

        # After parent's logic, check if all fields are filled
        if self.state == self.STATE_WAITING_USER_INPUT:
            if self.all_fields_filled():
                # Append a new assistant message
                self.chat_session.messages.append(Message(
                    role="assistant",
                    content=(
                        "It looks like you've provided all the key information for the story overview. "
                        "Would you like to revise anything, or proceed to the next step (characters)?"
                    ),
                    timestamp=datetime.now().isoformat()
                ))
                self.set_quick_responses(["Revise Something", "Proceed to Characters"])
            
            # Clean up ephemeral messages
            self.chat_session.messages = [
                msg for msg in self.chat_session.messages 
                if not getattr(msg, 'ephemeral', False)
            ]
            
            self.save_state()

    def get_last_response(self) -> dict:
        """Get the last assistant response from the chat history.
        
        Returns:
            dict: The last assistant message with content and any tool calls
        """
        # Iterate through messages in reverse to find the last assistant message
        for msg in reversed(self.chat_session.messages):
            if msg.role == "assistant":
                return {
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": msg.tool_calls or []
                }
        
        # Return None if no assistant message found
        return None
