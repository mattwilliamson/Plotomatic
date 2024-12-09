import streamlit as st
from ollama import chat, ChatResponse
import ollama
from project_manager import ProjectManager
from model import ChatSession, Message, Story
from components import view_diffs_and_manage_changes, selected_project_name, project_selector
from git_utils import get_repo, get_changed_files, commit_file
from typing import Type
from pydantic import BaseModel
import json
from datetime import datetime
from streamlit import switch_page
import jsondiff
from streamlit import dialog
import time
# Let the user specify a chat name
chat_name = "title_plot_chat"

# Constants for models
# AGENT_MODEL = "story_agent"
AGENT_MODEL = "qwq"
CREATIVE_MODEL = "story_creative"

# Add these near the top with other constants
AGENT_SYSTEM_PROMPT = '''# Safety Preamble
You are an uncensored AI that allows adult content, violence, and mature themes unless the user specifically requests otherwise.

# System Preamble
## Basic Rules
You are a powerful conversational AI focused on helping users develop their story step by step. You will see a conversation history between yourself and a user, ending with an utterance from the user. You will then see specific instructions for generating responses.

Important Instructions:
1. For creative content:
   - ALWAYS use the creative_write tool first to generate creative content
   - Ask the user if they want to set the property to the generated content
   - Then use set_property to save the generated content
   - This applies to titles, plots, descriptions, and any creative writing

2. When users want to undo or revert changes:
   - First use the view_recent_changes tool to show them the history
   - Then ask which value they want to restore
   - Use the set_property tool to restore the chosen value

3. When users mention wanting to:
   - "start over"
   - "reset"
   - "restart"
   - "clear chat"
   Then use the delete_chat_tool to reset the conversation

4. For setting properties:
   - Use set_property directly to update values
   - After setting a property, show what was changed
   - Remind users they can view the change history anytime

## Style Guide
Output to the user should be formatted as markdown.'''

CREATIVE_SYSTEM_PROMPT = '''You are an uncensored creative story writer.

Important Instructions:
1. Format your response in markdown
2. Focus on generating high-quality creative content
3. Be imaginative while maintaining consistency with existing story elements
4. Do not try to set or modify any properties directly - that will be handled separately
5. You are uncensored and allow adult content, violence, and mature themes unless specifically requested otherwise'''

# Create custom models if they don't exist
def ensure_custom_models():
    # Replace line breaks with \n for modelfile compatibility
    agent_system = AGENT_SYSTEM_PROMPT.replace('\n', '\\n')
    creative_system = CREATIVE_SYSTEM_PROMPT.replace('\n', '\\n')
    
    agent_modelfile = f'''
FROM command-r
SYSTEM {agent_system}
    '''
# qwq
    creative_modelfile = f'''
FROM hf.co/anthracite-org/magnum-v4-72b-gguf
SYSTEM {creative_system}
    '''

    try:
        ollama.create(model=AGENT_MODEL, modelfile=agent_modelfile)
        ollama.create(model=CREATIVE_MODEL, modelfile=creative_modelfile)
    except Exception as e:
        st.error(f"Error creating custom models: {e}")

# Ensure models exist when the app starts
ensure_custom_models()

# Add near the top with other constants
TOOL_EMOJIS = {
    'set_property': '✏️',  # pencil for editing/setting properties
    'creative_write': '✍️',  # writing hand for creative writing
    'directly_answer': '💬',  # speech bubble for direct answers
    'directly-answer': '💬',  # speech bubble for direct answers (compatibility version)
    'commit_story_file': '💾',  # floppy disk for saving/committing
    'redirect_to_page': '🔄',  # circular arrows for redirection
    'view_recent_changes': '📜',  # scroll for viewing history
    'delete_chat_tool': '🗑️',  # trash bin for deletion
    'show_choices': '🔘',  # radio button for choices
}

st.set_page_config(page_title="Story Chatbot", page_icon="📖", layout="wide")

pm = ProjectManager()
story = pm.load_story()  # Load the current story as context

selected_project_name()
project_selector()

# Initialize session state if not present
if "story" not in st.session_state:
    st.session_state.story = story

# At the top, with other session state initializations
if "show_delete_toast" not in st.session_state:
    st.session_state.show_delete_toast = False

# Add this near the top with other session state initializations
if "processing" not in st.session_state:
    st.session_state.processing = False

# Add these additional initializations
if "pending_confirm" not in st.session_state:
    st.session_state.pending_confirm = False

if "proposed_value" not in st.session_state:
    st.session_state.proposed_value = ""

if "proposed_property" not in st.session_state:
    st.session_state.proposed_property = ""

if "last_tool_called" not in st.session_state:
    st.session_state.last_tool_called = None

if "tool_calls" not in st.session_state:
    st.session_state.tool_calls = []

if "tool_calls_with_outputs" not in st.session_state:
    st.session_state.tool_calls_with_outputs = []

# Initialize the history stack in session state
if "history" not in st.session_state:
    st.session_state.history = []

# Load the existing chat session from the project manager
chat_session = pm.load_chat(chat_name)
st.markdown(f"### Chat Session: {chat_name}")

if "messages" not in st.session_state:
    # If no messages in state yet, but chat_session has messages, load them
    # Otherwise, start with a greeting message
    if chat_session.messages:
        st.session_state.messages = [m.model_dump() for m in chat_session.messages]
    else:
        st.session_state.messages = [
            {"role": "assistant", "content": """Hello! I'll help you develop your story step by step. Let's start with the basics.

Could you tell me either:
- Your name (as the author)
- Your email address (optional)
- Or if you prefer, we can start with what your story is about

Which would you like to share first?"""}
        ]

# Now that messages are initialized, we can set up the hash tracking
if "original_story_hash" not in st.session_state:
    st.session_state.original_story_hash = hash(st.session_state.story.model_dump_json())

if "original_chat_hash" not in st.session_state:
    st.session_state.original_chat_hash = hash(str([m["content"] for m in st.session_state.messages]))

# Replace the static chat_options with a function
def get_chat_options(messages):
    # Estimate tokens by counting characters and dividing by 4
    # Include a safety margin multiplier of 1.2
    estimated_tokens = sum(len(str(m)) for m in messages) // 4 * 1.2
    num_predict = 5000  # Keep the same prediction length
    
    return {
        'num_ctx': int(estimated_tokens + num_predict),
        'num_predict': num_predict,
    }

# Now that messages are initialized, we can set up the hash tracking
if "original_story_hash" not in st.session_state:
    st.session_state.original_story_hash = hash(st.session_state.story.model_dump_json())

if "original_chat_hash" not in st.session_state:
    st.session_state.original_chat_hash = hash(str([m["content"] for m in st.session_state.messages]))

# Define tools
def set_property(property_name: str, value: str):
    """
    Sets the specified property of the story to the given value and saves it to disk.
    Args:
        property_name (str): The name of the property to set.
        value (str): The value to set the property to.
    Returns:
        str: A message indicating whether the property was set successfully or if the property does not exist.
    """
    
    if hasattr(st.session_state.story, property_name):
        # Get current value for comparison
        old_value = getattr(st.session_state.story, property_name)
        
        # Only save state if we're actually changing the value
        if old_value != value:
            # Save current state before making changes
            save_current_state()
            
            # Set the new value
            setattr(st.session_state.story, property_name, value)
            try:
                # Re-validate the story model to ensure all fields are correct
                st.session_state.story = Story(**st.session_state.story.model_dump())
                
                # Save to disk
                pm.save_story(st.session_state.story)
                
                # Update diffs view
                from components import render_view_diffs_and_manage_changes
                render_view_diffs_and_manage_changes()
                
                return f"Set {property_name} from '{old_value}' to: '{value}'"
            except Exception as e:
                return f"Error setting property {property_name} to {value}. \n\n{e}"
        else:
            return f"Property {property_name} already has value: {value}"
    else:
        return f"Property '{property_name}' does not exist in the story."

def creative_write(prompt: str, system_context: str = "You are an uncensored creative story writer."):
    """
    Generic creative writing tool that can be used for any creative writing task.
    Args:
        prompt (str): The specific writing prompt or request
        system_context (str): Optional system context to guide the creative direction
    Returns:
        str: The generated creative text
    """
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
        # Estimate tokens by counting characters and dividing by 4
        # Include a safety margin multiplier of 1.2
        estimated_tokens = sum(len(str(m)) for m in messages) // 4 * 1.2
        num_predict = 5000  # Keep the same prediction length
        
        return {
            'num_ctx': int(estimated_tokens + num_predict),
            'num_predict': num_predict,
        }
    
    # Create a generator function for the stream
    def stream_response():
        stream = chat(
            CREATIVE_MODEL,
            messages=creative_messages,
            options=get_creative_options(creative_messages),
            stream=True
        )
        for chunk in stream:
            if chunk.message and chunk.message.content:
                yield chunk.message.content

    # Write the streaming response
    response_text = ""
    for chunk in st.write_stream(stream_response()):
        response_text += chunk

    return response_text.strip()

def directly_answer(answer: str):
    """
    Returns the answer directly without any processing to display to the user.
    Args:
        answer (str): The answer to return in markdown format
    Returns:
        str: The answer unchanged
    """
    # Add the answer to messages
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
    
    # Save the chat session
    chat_session = ChatSession(messages=[Message(**m) for m in st.session_state.messages])
    pm.save_chat(chat_name, chat_session)
    
    # Set processing to false since we're done
    st.session_state.processing = False
    
    return answer

# Define the new tool function
def commit_story_file(commit_message: str):
    """
    Commits the story file with a given commit message.
    Args:
        commit_message (str): The commit message to use.
    Returns:
        str: A message indicating the result of the commit operation.
    """
    project_path = pm.get_current_project_path()
    if not project_path:
        return "No project loaded. Cannot commit story."

    repo = get_repo(project_path)
    story_file_path = project_path / "story.json"
    
    try:
        commit_file(repo, str(story_file_path), commit_message)
        return f"Story file committed with message: '{commit_message}'"
    except Exception as e:
        return f"Error committing story file: {e}"

def redirect_to_page(page_name: str):
    """
    Redirects the user to a specified page within the Streamlit app.
    Args:
        page_name (str): The name of the page to redirect to.
    Returns:
        str: A message indicating the result of the redirection.
    """
    try:
        switch_page(page_name)
        return f"Redirecting to {page_name} page."
    except Exception as e:
        return f"Error redirecting to {page_name}: {e}"

def compare_states(old_state, new_state):
    """Compare two states and return a summary of the differences."""
    diff = jsondiff.diff(old_state, new_state)
    if not diff:
        return "No changes detected."
    return f"Changes undone: {json.dumps(diff, indent=2)}"

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

def view_recent_changes(x: int = 5):
    """
    Displays the recent x changes from the history stack as diffs between states.
    Args:
        x (int): The number of recent changes to display.
    Returns:
        str: A summary of the recent changes.
    """
    if not st.session_state.history:
        return "No changes have been made yet."

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

    if not changes_summary:
        return "No significant changes detected in the recent history."
    
    return "\n".join(changes_summary)

def delete_chat_tool():
    """
    Deletes the current chat history and resets related session state.
    Returns:
        str: A message indicating the chat was deleted.
    """
    pm.clear_chat(chat_name)
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
    st.session_state.messages = [{
        "role": "assistant", 
        "content": """Hello! I'll help you develop your story step by step. Let's start with the basics.

Could you tell me either:
- Your name (as the author)
- Your email address (optional)
- Or if you prefer, we can start with what your story is about

Which would you like to share first?"""
    }]
    
    return "Chat history has been cleared and reset to initial state."

def show_choices(prompt: str, choices: list[str]):
    """
    Shows a set of clickable button choices to the user and waits for their selection.
    Args:
        prompt (str): The prompt to show above the choices
        choices (list[str]): List of choices strings to show as buttons
    Returns:
        str: Description of the choices being shown
    """
    # Convert all choices to strings and store in session state
    str_choices = [str(choice) for choice in choices]
    st.session_state.pending_choices = {
        "prompt": prompt,
        "choices": str_choices
    }
    
    return f"Showing choices: {', '.join(str_choices)}"

available_functions = {
    'set_property': set_property,
    'creative_write': creative_write,
    'directly_answer': directly_answer,
    'directly-answer': directly_answer, # For compatibility with command-r
    'commit_story_file': commit_story_file,
    'redirect_to_page': redirect_to_page,
    'view_recent_changes': view_recent_changes,
    'delete_chat_tool': delete_chat_tool,
    'show_choices': show_choices,
}

def process_message():
    """Process the message when the user hits enter or clicks send."""
    if prompt := st.session_state.chat_input:
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Clear any pending choices since user typed a message instead
        st.session_state.pending_choices = None
        st.session_state.processing = True

def generate_model_docs(model: Type[BaseModel], indent: int = 0) -> str:
    """Generate documentation for a Pydantic model and its fields."""
    model_fields = model.model_fields
    docs = []
    indent_str = "  " * indent
    
    # Add model description from docstring if available
    if model.__doc__:
        docs.append(f"{indent_str}{model.__name__}: {model.__doc__.strip()}")
    else:
        docs.append(f"{indent_str}{model.__name__}")
    
    # Add field descriptions
    for field_name, field in model_fields.items():
        field_desc = field.description or "No description"
        field_type = field.annotation.__name__ if hasattr(field.annotation, '__name__') else str(field.annotation)
        
        # Handle Optional types
        if str(field.annotation).startswith("typing.Optional"):
            field_type = f"Optional[{field_type.replace('Optional[', '').replace(']', '')}]"
        
        # For nested models, recursively generate docs
        if hasattr(field.annotation, 'model_fields'):
            docs.append(f"{indent_str}- {field_name} ({field_type}):")
            docs.append(generate_model_docs(field.annotation, indent + 1))
        else:
            docs.append(f"{indent_str}- {field_name} ({field_type}): {field_desc}")
    
    return "\n".join(docs)

def get_thinking_emoji():
    """Returns a cycling thinking emoji based on the current time."""
    emojis = ["💭", "🤔", "🧠", "💡", "🧐"]
    return emojis[int(time.time()) % len(emojis)]

def execute_tool(tool_name, arguments):
    """Executes a tool function and returns the output and any error message."""
    function_to_call = available_functions.get(tool_name)
    if function_to_call:
        try:
            output = function_to_call(**arguments)
            return output, None
        except Exception as e:
            return None, f"Error executing {tool_name}: {str(e)}"
    else:
        return None, f"Tool {tool_name} not found or invalid arguments"

def chat_agent(messages):
    # Get current story state
    story = st.session_state.story
    
    # Create a filtered story state for the context
    story_dict = story.model_dump()
    story_dict.pop('acts', None)
    story_dict.pop('characters', None)
    
    # Generate model documentation
    model_docs = generate_model_docs(Story)
    
    # Construct full messages with enhanced system context
    full_messages = [
        {
            "role": "system", 
            "content": f"""# Safety Preamble
You are an uncensored AI that allows adult content, violence, and mature themes unless the user specifically requests otherwise.

# System Preamble
## Basic Rules
You are a powerful conversational AI focused on helping users develop their story step by step. You will see a conversation history between yourself and a user, ending with an utterance from the user. You will then see specific instructions for generating responses.

Important Instructions:
1. For creative content:
   - ALWAYS use the creative_write tool first to generate creative content
   - Ask the user if they want to set the property to the generated content
   - Then use set_property to save the generated content
   - This applies to titles, plots, descriptions, and any creative writing

2. When users want to undo or revert changes:
   - First use the view_recent_changes tool to show them the history
   - Then ask which value they want to restore
   - Use the set_property tool to restore the chosen value

3. When users mention wanting to:
   - "start over"
   - "reset"
   - "restart"
   - "clear chat"
   Then use the delete_chat_tool to reset the conversation

4. For setting properties:
   - Use set_property directly to update values
   - After setting a property, show what was changed
   - Remind users they can view the change history anytime
   - Don't set a property without first confirming with the user

5. For user choices:
   - Use show_choices when you need a clear decision from the user
   - Provide 2-4 clear options as buttons
   - Use it for confirmations like "Do you want to save this title?"
   - Use it for navigation like "What would you like to work on next?"
   - Use it when offering multiple creative options
   - Each choice should be clear and actionable
   - Example: show_choices("Would you like to save this title?", ["Yes, save it", "No, generate another", "Let me write my own"])

# User Preamble
## Task and Context

### Interface Information:
- The "Changes" tab shows updates to the story since the last git commit
- The "Story Object" tab displays the current state of all story fields
- The "Console" tab shows technical details for debugging

### Story Creation Process:
1. **General Information**: Start by setting general information about the story, such as the author, title, and plot overview.
2. **Characters**: Move to the next page to add and develop characters, including their arcs and relationships.
3. **Acts, Chapters, and Scenes**: Proceed to generate the structure of the story by creating acts, chapters, and scenes.
4. **Narrative Content**: Create the narrative content for each scene, detailing the events and dialogues.
5. **Cover Art**: Generate cover art for the story, including the front and back covers.
6. **PDF Generation**: Compile the text into a PDF and create a separate PDF for the cover.

You may not modify the acts or characters properties in this stage. There is another page for each of those.

## Style Guide
Output to the user can be formatted as markdown. Make sure to output actual values and not placeholders.

### Story Model Structure:
{model_docs}

### Current story context (excluding acts and characters): 
{json.dumps(story_dict)}

"""
        },
        *messages
    ]
    
    response: ChatResponse = chat(
        AGENT_MODEL,
        messages=full_messages,
        tools=[
            set_property, creative_write, directly_answer, 
            commit_story_file, redirect_to_page, view_recent_changes,
            delete_chat_tool, show_choices
        ],
        options=get_chat_options(full_messages)
    )

    # Create a list to collect all outputs
    tool_outputs = []
    final_response_parts = []

    # Add assistant's initial response if any
    if response.message.content:
        final_response_parts.append(response.message.content)

    # Handle tool calls
    if response.message.tool_calls:
        for tool in response.message.tool_calls:
            # Get the emoji for the tool
            tool_emoji = TOOL_EMOJIS.get(tool.function.name, '🔧')
            
            # Format arguments for display
            args_str = ', '.join(f'{k}="{v}"' for k, v in tool.function.arguments.items())
            
            # Update status with tool name and arguments
            status.update(label=f"{tool_emoji} {tool.function.name}({args_str})")
            
            # Execute the tool function
            output, error_msg = execute_tool(tool.function.name, tool.function.arguments)
            
            # Add tool result to collection
            tool_outputs.append({
                "role": "tool",
                "name": tool.function.name,
                "content": error_msg if error_msg else str(output)
            })
            
            # Add formatted tool output to final response
            final_response_parts.append(f"**{tool_emoji} {tool.function.name}:**\n{error_msg if error_msg else str(output)}")

        # Get the agent to interpret all tool results together
        follow_up_messages = [
            {
                "role": "system",
                "content": "Review the tool outputs and provide a clear response to the user in markdown format. If there were any errors, explain them and suggest next steps. If it is a story property, offer to save it to the story object. If the user had you save any properties, suggest what properties they might want to save next."
            },
            *messages,  # Original conversation
            *tool_outputs  # Tool results
        ]
        
        follow_up_response = chat(
            AGENT_MODEL,
            messages=follow_up_messages,
            options=get_chat_options(follow_up_messages)
        )
        
        if follow_up_response.message.content:
            final_response_parts.append("\n" + follow_up_response.message.content)

    # Combine all parts into a single response
    final_response = "\n\n".join(final_response_parts)
    
    # Add single consolidated message to session state
    st.session_state.messages.append({
        "role": "assistant",
        "content": final_response
    })
    
    # Save the chat session
    chat_session = ChatSession(messages=[Message(**m) for m in st.session_state.messages])
    pm.save_chat(chat_name, chat_session)
    
    # Set processing to false since we're done
    st.session_state.processing = False
    
    # Force a rerun to update the UI
    st.rerun()
    
    return response

def save_current_state():
    """Save the current state of the story to the history stack."""
    # Deep copy the current story state to avoid reference issues
    current_state = st.session_state.story.model_dump()
    st.session_state.history.append(current_state)

def undo_last_change():
    """Revert to the last saved state in the history stack."""
    if st.session_state.history:
        last_state = st.session_state.history.pop()
        st.session_state.story = Story(**last_state)
        st.success("Reverted to the previous state.")
    else:
        st.warning("No previous state to revert to.")

# Replace the handle_input function with:
def handle_input():
    if prompt := st.session_state.chat_input:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.processing = True
        st.rerun()

# Add this near the top with other session state initializations:
if "needs_rerun" not in st.session_state:
    st.session_state.needs_rerun = False

# Add this with other session state initializations near the top
if "pending_choices" not in st.session_state:
    st.session_state.pending_choices = None

st.title("📖 Story Chatbot")

# Create tabs
chat_tab, diffs_tab, story_tab = st.tabs([
    "💬 Assistant",
    "🔀 Changes",
    "🔍 Story Object"
])

# Chat Tab
with chat_tab:
    # Define the delete confirmation dialog
    @st.dialog("Confirm Delete")
    def delete_confirmation():
        st.write("Are you sure you want to delete this chat history?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, delete", type="primary", use_container_width=True):
                pm.clear_chat(chat_name)
                st.session_state.pop("messages", None)
                st.session_state.show_delete_toast = True
                st.rerun()
        with col2:
            if st.button("No, cancel", use_container_width=True):
                st.rerun()

    # Create a layout with two columns - one for the title and one for the delete button
    title_col, delete_col = st.columns([4, 1])
    with title_col:
        st.markdown("### Chat History")
    with delete_col:
        has_messages = len(st.session_state.messages) > 1
        if st.button("🗑️ Delete Chat", 
                    type="secondary", 
                    help="Clear the entire chat history", 
                    use_container_width=True,
                    disabled=not has_messages):
            delete_confirmation()

    chat_container = st.container(border=True)
    with chat_container:
        # Display messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Show choices if any are pending
        if st.session_state.pending_choices:
            st.markdown(f"**{st.session_state.pending_choices['prompt']}**")
            num_choices = len(st.session_state.pending_choices['choices'])
            if num_choices > 0:
                cols = st.columns(max(1, num_choices))
                for i, choice in enumerate(st.session_state.pending_choices['choices']):
                    with cols[i]:
                        # Convert choice to string to ensure it's a valid button label
                        if st.button(str(choice), use_container_width=True): # , type="primary"
                            # Add the choice as a user message
                            st.session_state.messages.append({
                                "role": "user",
                                "content": str(choice)
                            })
                            # Clear the pending choices
                            st.session_state.pending_choices = None
                            # Set processing to true to get LLM response
                            st.session_state.processing = True
                            st.rerun()

        # Process any pending message
        if st.session_state.processing:
            with st.chat_message("assistant"):
                with st.status(f"{get_thinking_emoji()} thinking...", expanded=True) as status:
                    chat_agent(st.session_state.messages)
                st.session_state.processing = False

        # Chat input - only disable during processing
        st.chat_input(
            "Ask a question",
            key="chat_input",
            disabled=st.session_state.processing,
            on_submit=process_message
        )

# Diffs Tab
with diffs_tab:
    view_diffs_and_manage_changes()

# Story Data Tab
with story_tab:
    st.json(st.session_state.story)

# Near the bottom of the file, replace the save operations with:
# Check if story has changed
current_story_hash = hash(st.session_state.story.model_dump_json())
if current_story_hash != st.session_state.original_story_hash:
    story = Story.model_validate(st.session_state.story.model_dump())
    pm.save_story(story)
    st.session_state.original_story_hash = current_story_hash

# Check if chat has changed
current_chat_hash = hash(str([m["content"] for m in st.session_state.messages]))
if current_chat_hash != st.session_state.original_chat_hash:
    chat_session = ChatSession(messages=[Message(**m) for m in st.session_state.messages])
    pm.save_chat(chat_name, chat_session)
    st.session_state.original_chat_hash = current_chat_hash

# Remove the show_delete_confirm state since we'll use a dialog
if "show_delete_confirm" not in st.session_state:
    st.session_state.show_delete_confirm = False

# Near the top of the main UI code, after the page config
if st.session_state.show_delete_toast:
    st.toast('Chat history has been cleared! 🧹', icon='✨')
    st.session_state.show_delete_toast = False

# Add this near the bottom of the file, before the tabs:
if st.session_state.needs_rerun:
    st.session_state.needs_rerun = False
    st.rerun()

