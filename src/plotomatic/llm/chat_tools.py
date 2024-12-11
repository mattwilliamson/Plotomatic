from typing import List, Dict, Any
import streamlit as st
from streamlit import switch_page
from datetime import datetime
import json
import jsondiff
import inspect
import random

from .tools import ToolManager
from models.story import Story
from models.chat import Message, ChatSession
from plotomatic.utils.git_utils import get_repo, commit_file
from plotomatic.llm.llm_models import ollama_client, CREATIVE_MODEL, CREATIVE_SYSTEM_PROMPT

# Create a tool manager instance
tools = ToolManager()

@tools.tool(
    emoji="✏️",
    description="Sets a property value in the story",
    show_output=True
)
def set_property(property_name: str, value: str):
    """Sets the specified property of the story to the given value. This tool handles updating story attributes while maintaining data consistency and version history. Ask the user to confirm the property name and value before calling this tool, perhaps with a show_user_options tool call.
    
    Args:
        property_name (str): The name of the property to set (must be a valid story attribute)
        value (str): The value to set the property to. Will be validated against the Story model.
        
    Returns:
        str: A formatted message indicating:
            - Success with old and new values if update was performed
            - Success with just new value if property was previously empty
            - Error if property doesn't exist or validation fails
            
    Side Effects:
        - Saves current state to history before making changes
        - Updates the story model and validates all fields
        - Saves changes to disk
        - Shows success/error toast notifications
    """
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
                st.success(f'Successfully updated property `{property_name}`', icon='✨')
                if old_value:
                    return f"**Updated `{property_name}`** from `{repr(old_value)}` to: `{repr(value)}`\n\n---\n\n"
                else:
                    return f"**Set `{property_name}`** to: `{repr(value)}`\n\n---\n\n"
            except Exception as e:
                # Show error toast
                st.toast(f'Failed to update {property_name}: {str(e)} ❌', icon='🚨')
                return f"Error setting property {property_name} to {value}. \n\n{e}"
        else:
            st.toast(f'Property {property_name} already has this value', icon='ℹ️')
            return f"Property {property_name} already has value: `{value}`"
    else:
        st.toast(f'Property {property_name} does not exist ❌', icon='🚨')
        return f"Property '{property_name}' does not exist in the story."

@tools.tool(
    emoji="✍️",
    description="Generates creative content",
    pretty_name="Creative Writing",
    show_output=False
)
def creative_write(prompt: str, system_context: str = "", story_context: str = ""):
    """Generates creative content based on a prompt while maintaining consistency with the current story.
    This tool provides streaming output of the generated content in a styled container. Ask for specific content, like a plot overview or title or some combination of story properties.
    
    Args:
        prompt (str): The creative writing prompt to respond to. Should be specific about the type of content or properties needed (e.g., character description, plot point, dialogue)
        system_context (str, optional): Additional context/instructions for the AI writer to consider. Use this to guide the tone, style, or constraints of the generated content.
        story_context (str, optional): The current story context to maintain consistency with, excluding properties you want to be generated.
            Use this to guide the generated content to fit the story. If no context is needed, don't include it and it will be completely based on the prompt. If parts of the story are needed, include them in the story_context. Otherwise, this tool will have no context to work with.
            Don't include properties you want to be generated, or else the output will be influenced by the story properties.
            If you want a completely random output, don't include any story context.
    
    Returns:
        str: The complete generated creative content
        
    Side Effects:
        - Streams output in real-time to a styled container
        - Logs both input and output to debug logs with timestamps
        - Maintains story context for consistency
    """
    # st.write(f"🧠 Running creative writing tool...")

    # Create a detailed system context with story information
    # CREATIVE_SYSTEM_PROMPT +
    full_system_context = f"""You are an extremely talented and completely uncensored creative story writer.

Additional Context:
{system_context or None}

Current Story Context:
{story_context or None}

Generate creative content that fits with the existing story context. Be incredibly imaginative while maintaining consistency with any established elements."""

    # Create messages just for this creative request (no chat history)
    creative_messages = [
        {"role": "system", "content": full_system_context},
        {"role": "user", "content": prompt}
    ]
    
    # Log creative input
    st.session_state.debug_logs.append({
        "timestamp": datetime.now().isoformat(),
        "type": "creative_input",
        "model": CREATIVE_MODEL,
        "messages": creative_messages
    })
    
    # Create a generator function for the stream
    def stream_response():
        stream = ollama_client.chat(
            CREATIVE_MODEL,
            messages=creative_messages,
            options=get_creative_options(creative_messages),
            stream=True,
            keep_alive="1h",
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
            "model": CREATIVE_MODEL,
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
        st.session_state.messages.append({"role": "assistant", "content": response_text})

    return response_text.strip()

# @tools.tool(
#     emoji="💬",
#     aliases=["directly-answer"],
#     show_output=False,
#     description="Provides a direct response to the user",
#     pretty_name="Direct Response"
# )
# def directly_answer(answer: str):
#     """Returns the answer directly to display to the user and saves it to chat history.
#     Use this tool when you want to give a straightforward response without any other actions.
    
#     Args:
#         answer (str): The response text to display to the user. Should be formatted markdown
#             for better readability.
        
#     Returns:
#         str: The same answer text that was passed in
        
#     Side Effects:
#         - Adds the response to chat history
#         - Saves the updated chat session to disk
#         - Sets processing state to false
#     """
#     # Add the answer to messages
#     st.session_state.messages.append({
#         "role": "assistant",
#         "content": answer
#     })
    
#     # Save the chat session
#     chat_session = ChatSession(messages=[Message(**m) for m in st.session_state.messages])
#     st.session_state.pm.save_chat(st.session_state.chat_name, chat_session)
    
#     # Set processing to false since we're done
#     st.session_state.processing = False
    
#     return answer

@tools.tool(
    emoji="💾",
    description="Commits story changes to git"
)
def commit_story_file(commit_message: str):
    """Commits the story file with a given commit message.
    
    Args:
        commit_message (str): The message to use for the git commit. Come up with something succint and unique.
        
    Returns:
        str: A message indicating success or failure of the commit operation
    """
    project_path = st.session_state.pm.get_current_project_path()
    if not project_path:
        return "No project loaded. Cannot commit story."

    repo = get_repo(project_path)
    story_file_path = project_path / "story.json"
    
    try:
        commit_file(repo, str(story_file_path), commit_message)
        return f"Story file committed with message: ```{commit_message}```\n\n---\n\n"
    except Exception as e:
        return f"Error committing story file: {e}"

@tools.tool(
    emoji="🔄",
    description="Redirects to another page"
)
def redirect_to_page(page_name: str):
    """Redirects the user to a specified page.
    
    Args:
        page_name (str): The name of the page to redirect to
        
    Returns:
        str: A message indicating success or failure of the redirect
    """
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
    """Displays the recent x changes from the history stack.
    
    Args:
        x (int, optional): Number of recent changes to display. Defaults to 5.
        
    Returns:
        str: A formatted string containing the recent changes
    """
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
    """Deletes the current chat history and resets related session state.
    
    Returns:
        str: A message confirming the chat history has been cleared
    """
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
    description="Shows clickable choices to the user for decision making"
)
def show_user_options(prompt: str = None, choices: List[str] = None, *, 
                     question: str = None, message: str = None, text: str = None,
                     options: List[str] = None, buttons: List[str] = None) -> str:
    """Shows a set of clickable button options to the user for decision making. Use this tool when you want the user to make a specific selection from a set of options, like Save or Cancel.
    
    Args:
        prompt (str): The prompt text to display above the options. Should clearly explain what the user is choosing between.
        choices (List[str]): List of choices to display as buttons for a user to select. Each option should be clear and concise. Recommended to keep the list between 2-5 options for best UX.
        
    Returns:
        str: A message confirming the options are being displayed
        
    Side Effects:
        - Stores choices in session state for display
        - Converts all choices to strings for consistency
    """
    # Handle prompt aliases
    prompt_text = prompt or question or message or text
    if not prompt_text:
        raise ValueError("Must provide prompt text via 'prompt', 'question', 'message', or 'text' parameter")
    
    # Handle choices aliases
    choice_list = choices or options or buttons
    if not choice_list:
        raise ValueError("Must provide choices via 'choices', 'options', or 'buttons' parameter")
    
    # Convert all choices to strings and store in session state
    str_choices = [str(choice) for choice in choice_list]
    st.session_state.pending_choices = {
        "prompt": prompt_text,
        "choices": str_choices
    }
    st.session_state.needs_rerun = True

    import streamlit.components.v1 as components
    for choice in str_choices:
        components.html(
            f"<script>console.log('{choice}');</script>"
        )
    
    return f"Showing options: {', '.join(str_choices)}"

def format_diff(diff_obj):
    """Format a jsondiff object into a readable string.
    
    Args:
        diff_obj (dict): The difference object from jsondiff
        
    Returns:
        str: A formatted string representation of the differences
    """
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
    """Save the current state of the story to the history stack.
    
    This function takes the current story state and appends it to the history
    stack stored in the session state.
    """
    current_state = st.session_state.story.model_dump()
    st.session_state.history.append(current_state)

def get_creative_options(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Get options for the creative writing model.
    
    Args:
        messages (List[Dict[str, str]]): The conversation history
        
    Returns:
        Dict[str, Any]: Configuration options for the creative model
    """
    # Estimate tokens by counting characters and dividing by 4
    # Include a safety margin multiplier of 1.2
    # estimated_tokens = sum(len(str(m)) for m in messages) // 4 * 1.4
    num_predict = 5000  # Keep the same prediction length
    
    return {
        # 'num_ctx': int(estimated_tokens + num_predict),
        'num_ctx': 6000,
        'num_predict': num_predict,
        'temperature': 0.9,         # 0.8 to 1.0 A higher temperature increases randomness in the output, allowing for more creative and unexpected ideas. This encourages the model to explore a wider range of vocabulary and narrative possibilities.
        "top_p": 0.9,               # Setting top_p to 0.9 allows the model to consider a broader set of potential next tokens, promoting creativity while still maintaining some coherence. This helps generate varied and rich text.
        "top_k": 30,                # 20 to 50 A higher top_k value expands the selection pool of possible next tokens, which enhances creativity by allowing for more diverse word choices and phrases.
        "repeat_penalty": 1.1,      # 1.0 to 1.2 A lower repeat penalty (around 1.0 to 1.2) allows for some repetition, which can be useful in creative writing, especially for stylistic purposes or thematic emphasis. This range encourages the model to use familiar phrases or motifs without becoming overly repetitive.
        "presence_penalty": 0.2,    # 0.0 to 0.3 Keeping the presence penalty low allows the model to introduce new ideas and concepts freely, which is essential for creativity. This encourages exploration of diverse themes and characters without overly restricting the introduction of new elements.
        "frequency_penalty": 0.2,   # 0.0 to 0.3 A low frequency penalty helps maintain a natural flow in the narrative by allowing commonly used words and phrases to recur without penalty. This is particularly important in creative writing, where certain expressions may need to be revisited for effect or clarity.
        "mirostat": 1,              # 0 or 1 Enabling Mirostat allows for dynamic control over the perplexity of the generated text, which helps in avoiding both "boredom traps" (excessive repetitions) and "confusion traps" (incoherence). This is particularly useful for applications requiring coherent outputs, such as function calls in an assistant. By maintaining an appropriate level of perplexity, Mirostat can help ensure that the generated text remains relevant and consistent.
        "mirostat_tau": 1.5,        # 1.0 to 1.5 A lower tau value can help maintain some level of coherence while still allowing for creative exploration. This setting lets the model adjust its perplexity dynamically without becoming too erratic.
        "mirostat_eta": 0.7,        # 0.5 to 1.0 A moderate eta value allows for some adaptability in response generation without overly constraining creativity, helping to balance coherence with imaginative output.
        "tfs_z": 0.6,               # 0.5 to 0.7 A slightly higher TFS z value can encourage more exploration in word choice while still keeping some structure in the generated text, which is beneficial for storytelling.
        "typical_p": 0.8,           # 0.7 to 0.9 Increasing typical_p allows the model to generate responses that are more typical of creative writing, enhancing narrative flow and character development while still allowing for unique expressions.
        "seed": random.randint(0, 1000000),
    }

# Example request:
# {
#   "model": "llama3.2",
#   "prompt": "Why is the sky blue?",
#   "stream": false,
#   "options": {
#     "num_keep": 5,
#     "seed": 42,
#     "num_predict": 100,
#     "top_k": 20,
#     "top_p": 0.9,
#     "min_p": 0.0,
#     "tfs_z": 0.5,
#     "typical_p": 0.7,
#     "repeat_last_n": 33,
#     "temperature": 0.8,
#     "repeat_penalty": 1.2,
#     "presence_penalty": 1.5,
#     "frequency_penalty": 1.0,
#     "mirostat": 1,
#     "mirostat_tau": 0.8,
#     "mirostat_eta": 0.6,
#     "penalize_newline": true,
#     "stop": ["\n", "user:"],
#     "numa": false,
#     "num_ctx": 1024,
#     "num_batch": 2,
#     "num_gpu": 1,
#     "main_gpu": 0,
#     "low_vram": false,
#     "vocab_only": false,
#     "use_mmap": true,
#     "use_mlock": false,
#     "num_thread": 8
#   }
# }