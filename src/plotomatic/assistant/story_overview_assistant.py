# assistant/story_overview_assistant.py

from .base_assistant import BaseChatAssistant
from .states import AssistantState
from plotomatic.models.story import Story
from plotomatic.models.chat import Message
from .tools import tools
from pathlib import Path
import json
from datetime import datetime

class StoryOverviewAssistant(BaseChatAssistant):
    """
    Subclass that focuses on filling out the high-level overview of the story
    (e.g., title, genre, plot_overview, etc.).
    """

    MODEL = "llama3.3"  # Override the model at the class level

    # A system prompt specialized for story overview
    STORY_OVERVIEW_SYSTEM_PROMPT = """You are responsible for helping the user set the title, plot_overview, author and other high level properties of the story.
You are only allowed to set the top level properties in the story object.
You may not modify the acts or characters properties in this stage. There is another page for each of those.
You may, however inject a small number of characters or other details into the plot_overview by appending to it in order to help bootstrap the story.

If a user asks you to make up a story, just start with the plot_overview and then ask the user if they want to save it by calling set_property with the property "plot_overview". You may also set the title property if it is blank and ask to save it.

Important Rules:
- Don't call set_property without letting the user know you are doing it
- Make sure it is a valid property name
- Be extra cautious about calling set_property with destructive operations like setting a property to an empty string or None
- Only call set_property if the new value is different from the old value
- If set_property is dependent on a previous creative_write, then you must call creative_write first

After each tool call, you MUST:
- Validate that the output matches what you needed
- If the output is not satisfactory, call it again with a more specific prompt
- If it seems like the output is good, then ask the user if they approve or solicit a change with a show_user_options tool call
"""

    @classmethod
    def load_for_project(cls, project_path: Path) -> 'StoryOverviewAssistant':
        """Factory method to load or create an assistant for a specific project"""
        assistant_state_path = project_path / "story_overview_state.json"
        
        assistant = cls(
            storage_path=str(assistant_state_path)
        )
        
        # Register all available tools
        for tool_name, tool_func in tools.available_functions.items():
            assistant.register_tool(tool_func)
            
        return assistant

    def __init__(self, storage_path="story_overview_state.json"):
        super().__init__(storage_path=storage_path,
                         system_prompt=self.STORY_OVERVIEW_SYSTEM_PROMPT)
        self.story = Story()  # Will be set from outside

    def all_fields_filled(self) -> bool:
        """
        Check if the minimal required fields (title, genre, plot_overview, etc.) are filled.
        """
        required_fields = ["title", "genre", "plot_overview"]
        for f in required_fields:
            if not getattr(self.story, f, None):
                return False
        return True

    def run(self):
        """
        Override run to:
        1. Check if this is the first message and generate a greeting if needed
        2. Run normal assistant logic
        3. Check if all fields are filled after completion
        """
        # If this is the first run and no messages exist, generate initial greeting
        if not self.chat_session.messages and self.state == self.STATE_GENERATING_OUTPUT:
            if not self.story.title:
                self.chat_session.messages.append(Message(
                    role="assistant",
                    content=(
                        "I notice that your story's title is currently empty. "
                        "Would you like help coming up with a title?"
                    ),
                    timestamp=datetime.now().isoformat()
                ))
                self.state = self.STATE_WAITING_USER_INPUT
                self.save_state()
                return

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
