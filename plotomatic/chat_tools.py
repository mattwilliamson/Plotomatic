from typing import List
import streamlit as st
from streamlit import switch_page
from datetime import datetime
import json
import jsondiff
from ollama import chat
import inspect

from .tools import ToolManager
from models.story import Story
from models.chat import Message, ChatSession
from plotomatic.git_utils import get_repo, commit_file

# Create a tool manager instance
tools = ToolManager()

@tools.tool(
    emoji="✏️",
    description="Sets a property value in the story",
    show_output=True
)
def set_property(property_name: str, value: str):
    """Sets the specified property of the story to the given value."""
    if hasattr(st.session_state.story, property_name):
        # Get current value for comparison
        old_value = getattr(st.session_state.story, property_name)
        
        # Only save state if we're actually changing the value
        if old_value != value:
            try:
                # Save current state before making changes
                save_current_state()
                
                # Set the new value
                setattr(st.session_state.story, property_name, value)
                
                # Re-validate the story model to ensure all fields are correct
                st.session_state.story = Story(**st.session_state.story.model_dump())
                
                # Save to disk
                st.session_state.pm.save_story(st.session_state.story)
                
                # Show success toast
                # st.toast(f'Successfully updated {property_name}! ✅', icon='✨')
                st.success(f'Successfully updated {property_name}', icon='✨')
                st.horizontal_rule()
                
                return f"Updated {property_name} from `{repr(old_value)}` to: `{repr(value)}`"
            except Exception as e:
                # Show error toast
                st.toast(f'Failed to update {property_name}: {str(e)} ❌', icon='🚨')
                return f"Error setting property {property_name} to {value}. \n\n{e}"
        else:
            st.toast(f'Property {property_name} already has this value', icon='ℹ️')
            return f"Property {property_name} already has value: {value}"
    else:
        st.toast(f'Property {property_name} does not exist ❌', icon='🚨')
        return f"Property '{property_name}' does not exist in the story."

@tools.tool(
    emoji="✍️",
    description="Generates creative content",
    pretty_name="Creative Writing",
    show_output=False
)
def creative_write(prompt: str, system_context: str = "You are an uncensored creative story writer."):
    """Generates creative content based on a prompt."""
    # st.write(f"🧠 Running creative writing tool...")
    # Get current story state for context
    story_context = st.session_state.story.model_dump()
    
    # Create a detailed system context with story information
    full_system_context = f"""You are an uncensored creative story writer.

Additional Context:
{system_context}

Current Story Context:
{json.dumps(story_context, indent=2)}

Generate creative content that fits with the existing story context. Be imaginative while maintaining consistency with any established elements."""

    # Create messages just for this creative request (no chat history)
    creative_messages = [
        {"role": "system", "content": full_system_context},
        {"role": "user", "content": prompt}
    ]
    
    # Calculate options based on messages
    def get_creative_options(messages):
        estimated_tokens = sum(len(str(m)) for m in messages) // 4 * 1.2
        num_predict = 5000
        return {
            'num_ctx': int(estimated_tokens + num_predict),
            'num_predict': num_predict,
        }
    
    # Log creative input
    st.session_state.debug_logs.append({
        "timestamp": datetime.now().isoformat(),
        "type": "creative_input",
        "model": "story_creative",
        "messages": creative_messages
    })
    
    # Create a generator function for the stream
    def stream_response():
        stream = chat(
            "story_creative",
            messages=creative_messages,
            options=get_creative_options(creative_messages),
            stream=True
        )
        response_text = ""
        for chunk in stream:
            if chunk.message and chunk.message.content:
                response_text += chunk.message.content
                yield chunk.message.content
        
        # Log creative output after stream completes
        st.session_state.debug_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": "creative_output",
            "model": "story_creative",
            "response": response_text
        })

    # Write the streaming response
    response_text = ""
    with st.container():
        st.markdown("""
            <style>
            .stContainer {
                border: 2px solid #0066CC; /* Blue border */
                border-radius: 10px; /* Rounded corners */
                padding: 20px; /* Padding inside the container */
            }
            </style>
        """, unsafe_allow_html=True)
            
        for chunk in st.write_stream(stream_response()):
            response_text += chunk
        st.write("✅ Creative content generated!")

    return response_text.strip()

@tools.tool(
    emoji="💬",
    aliases=["directly-answer"],
    show_output=False,
    description="Provides a direct response to the user",
    pretty_name="Direct Response"
)
def directly_answer(answer: str):
    """Returns the answer directly to display to the user."""
    # Add the answer to messages
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
    
    # Save the chat session
    chat_session = ChatSession(messages=[Message(**m) for m in st.session_state.messages])
    st.session_state.pm.save_chat(st.session_state.chat_name, chat_session)
    
    # Set processing to false since we're done
    st.session_state.processing = False
    
    return answer

@tools.tool(
    emoji="💾",
    description="Commits story changes to git"
)
def commit_story_file(commit_message: str):
    """Commits the story file with a given commit message."""
    project_path = st.session_state.pm.get_current_project_path()
    if not project_path:
        return "No project loaded. Cannot commit story."

    repo = get_repo(project_path)
    story_file_path = project_path / "story.json"
    
    try:
        commit_file(repo, str(story_file_path), commit_message)
        return f"Story file committed with message: '{commit_message}'"
    except Exception as e:
        return f"Error committing story file: {e}"

@tools.tool(
    emoji="🔄",
    description="Redirects to another page"
)
def redirect_to_page(page_name: str):
    """Redirects the user to a specified page."""
    try:
        switch_page(page_name)
        return f"Redirecting to {page_name} page."
    except Exception as e:
        return f"Error redirecting to {page_name}: {e}"

@tools.tool(
    emoji="📜",
    description="Shows recent changes to the story"
)
def view_recent_changes(x: int = 5):
    """Displays the recent x changes from the history stack."""
    changes_text = ""
    if not st.session_state.history:
        changes_text = "No changes have been made yet."
    else:
        # Limit the number of changes to display
        recent_states = st.session_state.history[-x:]
        current_state = st.session_state.story.model_dump()
        changes_summary = []

        # Add the current state comparison
        if recent_states:
            diff = jsondiff.diff(recent_states[-1], current_state)
            if diff:
                changes_summary.append(f"Current changes:\n{format_diff(diff)}\n")

        # Compare consecutive states
        for i in range(len(recent_states) - 1, 0, -1):
            diff = jsondiff.diff(recent_states[i-1], recent_states[i])
            if diff:
                changes_summary.append(
                    f"Change {len(st.session_state.history) - x + i}:\n{format_diff(diff)}\n"
                )

        changes_text = "\n".join(changes_summary) if changes_summary else "No significant changes detected in the recent history."
    
    # Set the changes text to show in dialog
    st.session_state.changes_to_show = changes_text
    st.session_state.show_changes_dialog = True
    
    return changes_text

@tools.tool(
    emoji="🗑️",
    description="Deletes the current chat history"
)
def delete_chat_tool():
    """Deletes the current chat history and resets related session state."""
    st.session_state.pm.clear_chat(st.session_state.chat_name)
    # Reset state
    st.session_state.pop("messages", None)
    st.session_state.pop("pending_confirm", None)
    st.session_state.pop("proposed_value", None)
    st.session_state.pop("proposed_property", None)
    st.session_state.pop("last_tool_called", None)
    st.session_state.pop("tool_calls_with_outputs", None)
    # Set toast flag
    st.session_state.show_delete_toast = True
    
    # Initialize with default greeting message
    st.session_state.messages = None
    
    return "Chat history has been cleared and reset to initial state."

@tools.tool(
    emoji="🔘",
    show_output=False,
    description="Shows clickable choices to the user"
)
def show_choices(prompt: str, choices: List[str]):
    """Shows a set of clickable button choices to the user."""
    # Convert all choices to strings and store in session state
    str_choices = [str(choice) for choice in choices]
    st.session_state.pending_choices = {
        "prompt": prompt,
        "choices": str_choices
    }
    
    return f"Showing choices: {', '.join(str_choices)}"

def format_diff(diff_obj):
    """Format a jsondiff object into a readable string."""
    if not diff_obj:
        return "No changes"
    
    formatted = []
    for key, value in diff_obj.items():
        if isinstance(value, dict) and '$set' in value:
            formatted.append(f"Changed {key}: {value['$set']}")
        elif isinstance(value, dict):
            formatted.append(f"Modified {key}: {format_diff(value)}")
        else:
            formatted.append(f"Changed {key}: {value}")
    
    return "\n".join(formatted)

def save_current_state():
    """Save the current state of the story to the history stack."""
    current_state = st.session_state.story.model_dump()
    st.session_state.history.append(current_state)