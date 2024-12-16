# assistant/tools.py

from typing import List, Dict, Any
from datetime import datetime

from .tool_manager import ToolManager
from plotomatic.models import Story

# Create a tool manager instance
tools = ToolManager()

@tools.tool(
    emoji="✏️",
    description="Sets a property value in the story",
    show_output=True
)
def set_property(property_name: str, value: str):
    """Sets the specified property of the story to the given value. This tool handles updating story attributes while maintaining data consistency and version history.
    
    Args:
        property_name (str): The name of the property to set (must be a valid story attribute)
        value (str): The value to set the property to. Will be validated against the Story model.
        
    Returns:
        str: A formatted message indicating:
            - Success with old and new values if update was performed
            - Success with just new value if property was previously empty
            - Error if property doesn't exist or validation fails
    """
    # Import BaseAssistant here to avoid circular import
    from .base_assistant import BaseAssistant
    # Get the current assistant instance from the base class
    assistant = BaseAssistant.get_current()
    story = assistant.story

    if hasattr(story, property_name):
        # Get current value for comparison
        old_value = getattr(story, property_name)
        
        # Only save state if we're actually changing the value
        if old_value != value:
            try:
                # Save current state before making changes
                save_current_state()
                
                # Set the new value
                setattr(story, property_name, value)
                
                # Re-validate the story model to ensure all fields are correct
                story = Story(**story.model_dump())
                assistant.story = story
                
                # Set success status for UI
                assistant.set_status('success', f'Successfully updated property `{property_name}`')
                
                if old_value:
                    return f"**Updated `{property_name}`** from `{repr(old_value)}` to: `{repr(value)}`\n\n---\n\n"
                else:
                    return f"**Set `{property_name}`** to: `{repr(value)}`\n\n---\n\n"
            except Exception as e:
                # Set error status for UI
                assistant.set_status('error', f'Failed to update {property_name}: {str(e)}')
                return f"Error setting property {property_name} to {value}. \n\n{e}"
        else:
            assistant.set_status('info', f'Property {property_name} already has this value')
            return f"Property {property_name} already has value: `{value}`"
    else:
        assistant.set_status('error', f'Property {property_name} does not exist')
        return f"Property '{property_name}' does not exist in the story."

@tools.tool(
    emoji="✍️",
    description="Generates creative content",
    pretty_name="Creative Writing",
    show_output=False
)
def creative_write(prompt: str, system_context: str = "", story_context: str = ""):
    """Generates creative content based on a prompt."""
    return "Creative text"  # placeholder

def add_requirement(story_json: str, requirement: str) -> str:
    """
    Append a user requirement to the story's requirements list.
    
    Args:
        story_json: JSON-serialized Story object
        requirement: The requirement to add
    
    Returns:
        str: The updated JSON-serialized Story object
    """
    return story_json  # placeholder

def format_diff(diff_obj):
    """Format a jsondiff object into a readable string."""
    # ... implementation stays the same ...

def save_current_state():
    """Save the current state of the story to the history stack."""
    # ... implementation stays the same ...

def get_creative_options(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Get options for the creative writing model."""
    # ... implementation stays the same ...
