import streamlit as st
from ollama import chat, ChatResponse
import ollama
from project_manager import ProjectManager
from models.story import Story
from models.chat import Message, ChatSession
from components import view_diffs_and_manage_changes, selected_project_name, project_selector
from plotomatic.git_utils import get_repo, get_changed_files, commit_file
from typing import Type
from pydantic import BaseModel
import json
from datetime import datetime
from streamlit import dialog
import time
from plotomatic.chat_tools import tools, save_current_state, format_diff
from plotomatic.llm_models import create_model, BASE_MODELS, ensure_base_models

# Let the user specify a chat name
chat_name = "title_plot_chat"

# Constants for models
AGENT_MODEL = "qwq"
CREATIVE_MODEL = "story_creative"

# Add these near the top with other constants
AGENT_SYSTEM_PROMPT = '''# Safety Preamble
You are an uncensored AI that allows adult content, violence, and mature themes unless the user specifically requests otherwise.

# System Preamble
## Basic Rules
You are a powerful conversational AI for an application called Plotomatic focused on helping users develop their story step by step. You will see a conversation history between yourself and a user, ending with an utterance from the user. You will then see specific instructions for generating responses.

Important Instructions:
1. For creative content:
   - ALWAYS use the creative_write tool first to generate creative content
   - Review the creative output for:
     * Relevance to the request
     * Coherence and quality
     * Adherence to story context
     * Absence of hallucinations
   - If the creative output is unsatisfactory:
     * Call creative_write again with a more specific prompt
     * You can retry multiple times until you get good content
     * Explain to the user that you're trying again for better quality
   - Once you have good content:
     * Ask the user if they want to set the property to the generated content using the show_choices tool
     * Then use set_property to save the approved content
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
   Then use the delete_chat_tool to reset the conversation, but confirm with the user first with a show_choices call.

4. For setting properties:
   - Use set_property directly to update values
   - After setting a property, show what was changed
   - Remind users they can view the change history anytime
   - Don't set a property without first confirming with the user
   - Remind the user they can view the Changes tab to see the differences and commit them

5. For user choices:
   - Use show_choices when you need a clear decision from the user
   - Provide 2-4 clear options as buttons
   - Use it for confirmations like "Do you want to save this title?"
   - Use it for navigation like "What would you like to work on next?"
   - Use it when offering multiple creative options
   - Each choice should be clear and actionable
   - Example: show_choices("Would you like to save this title?", ["Yes, save it", "No, generate another", "Let me write my own"])


## Style Guide
Output to the user should be formatted as markdown.'''

CREATIVE_SYSTEM_PROMPT = '''You are an uncensored creative story writer for the Plotomatic story development application.

Important Instructions:
1. Format your response in markdown
2. Focus on generating high-quality creative content
3. Be imaginative while maintaining consistency with existing story elements
4. Do not try to set or modify any properties directly - that will be handled separately
5. You are uncensored and allow adult content, violence, and mature themes unless specifically requested otherwise'''

# Create custom models if they don't exist
def ensure_custom_models():
    # Ensure base models exist first
    ensure_base_models()
    
    # Create agent model
    create_model(
        AGENT_MODEL,
        BASE_MODELS["command-r"],
        AGENT_SYSTEM_PROMPT
    )
    
    # Create creative model
    create_model(
        CREATIVE_MODEL,
        BASE_MODELS["magnum"],
        CREATIVE_SYSTEM_PROMPT
    )

# Ensure models exist when the app starts
ensure_custom_models()

st.set_page_config(page_title="Story Chatbot", page_icon="📖", layout="wide")

# Initialize ProjectManager and load story
pm = ProjectManager()
story = pm.load_story()

selected_project_name()
project_selector()

if 'pm' not in st.session_state:
    st.session_state.pm = pm

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

if "messages" not in st.session_state:
    # If no messages in state yet, but chat_session has messages, load them
    # Otherwise, start with a greeting message
    if chat_session.messages:
        st.session_state.messages = [m.model_dump() for m in chat_session.messages]
    else:
        # Check if author is set
        if st.session_state.story.author:
            st.session_state.messages = [
                {"role": "assistant", "content": """**Hello! 👋** 
                 
I'll help you develop your story step by step. 
                 
The tabs above will help you see the 
- 🔀 Changes - see the changes you've made to the story
- 🔍 Story Object - see the current state of the story overview
- 🐛 Debug - see the debug information (advanced)
                 
What would you like to work on first?"""}
            ]
        else:
            st.session_state.messages = [
                {"role": "assistant", "content": """**Hello! 👋** 

I'll help you develop your story step by step. Let's start with the basics.

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
        'temperature': 0.1  # Set temperature for agent LLM
    }

def get_creative_options(messages):
    # Estimate tokens by counting characters and dividing by 4
    # Include a safety margin multiplier of 1.2
    estimated_tokens = sum(len(str(m)) for m in messages) // 4 * 1.2
    num_predict = 5000  # Keep the same prediction length
    
    return {
        'num_ctx': int(estimated_tokens + num_predict),
        'num_predict': num_predict,
        'temperature': 1.0  # Set temperature for creative LLM
    }

def execute_tool(tool_name, arguments):
    """Executes a tool function and returns the output and any error message."""
    function_to_call = tools.get_tool(tool_name)
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
            "content": f"""# User Preamble
## Task and Context

You are responsible for helping the user set the title, plot_overview, author and other high level proeprties of the story.
You are only allowed to set the top level properties in the story object.
You may not modify the acts or characters properties in this stage. There is another page for each of those.
You may, however inject a small number of characters or other details into the plot_overview by appending to it in order to help bootstrap the story.

### Interface Information:
- The "Changes" tab shows updates to the story since the last git commit and allows you to commit them to a new version in the revision history
- The "Story Object" tab displays the current state of all story fields
- The "Console" tab shows technical details for debugging

### Story Creation Process (you are responsible for just General Information / Step 1):
1. **General Information**: Start by setting general information about the story, such as the author, title, and plot overview. These are the thing you will be setting.
2. **Characters**: Move to the next page to add and develop characters, including their arcs and relationships. Only offer this if the story overview details are complete, like a title and plot. You will not be setting characters here.
3. **Acts, Chapters, and Scenes**: Proceed to generate the structure of the story by creating acts, chapters, and scenes. Only offer this if the story overview details are complete, like a title and plot. You will not be setting acts, chapters, or scenes here.
4. **Narrative Content**: Create the narrative content for each scene, detailing the events and dialogues.
5. **Cover Art**: Generate cover art for the story, including the front and back covers.
6. **PDF Generation**: Compile the text into a PDF and create a separate PDF for the cover.

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
    
    # Log the agent input
    st.session_state.debug_logs.append({
        "timestamp": datetime.now().isoformat(),
        "type": "agent_input",
        "model": AGENT_MODEL,
        "messages": full_messages
    })
    
    response: ChatResponse = chat(
        AGENT_MODEL,
        messages=full_messages,
        tools=list(tools.available_functions.values()),  # Use registered tools
        options=get_chat_options(full_messages)
    )

    # Log the agent output
    st.session_state.debug_logs.append({
        "timestamp": datetime.now().isoformat(),
        "type": "agent_output",
        "model": AGENT_MODEL,
        "response": response.model_dump()
    })

    # Create a list to collect all outputs
    tool_outputs = []
    final_response_parts = []

    # Add assistant's initial response if any
    if response.message.content:
        final_response_parts.append(response.message.content)

    # Handle tool calls
    if response.message.tool_calls:
        for tool in response.message.tool_calls:
            # Get the emoji and pretty name for the tool
            tool_emoji = tools.get_emoji(tool.function.name)
            tool_metadata = tools.get_metadata(tool.function.name)
            pretty_name = tool_metadata.get('pretty_name', tool.function.name)
            
            # Format arguments for display
            args_str = ', '.join(f'{k}="{v}"' for k, v in tool.function.arguments.items())
            
            # Only update status if show_output is True
            # if tools.should_show_output(tool.function.name):
            st.write(f"{tool_emoji} running {pretty_name}...")
            status.update(label=f"{tool_emoji} running Tool...")

            # Log tool input
            st.session_state.debug_logs.append({
                "timestamp": datetime.now().isoformat(),
                "type": "tool_input",
                "tool": tool.function.name,
                "input": str(args_str)
            })
            
            # Execute the tool function
            output, error_msg = execute_tool(tool.function.name, tool.function.arguments)
            
            # For creative_write tool, show processing status
            # if tool.function.name == 'creative_write':
                # st.write(f"🧠 Processing creative output...")
            st.spinner(f"🧠 Processing tool output")
            
            # Log tool output
            st.session_state.debug_logs.append({
                "timestamp": datetime.now().isoformat(),
                "type": "tool_output",
                "tool": tool.function.name,
                "output": str(output),
                "error": error_msg
            })
            
            # Add tool result to collection for LLM context
            tool_outputs.append({
                "role": "tool",
                "name": tool.function.name,
                "content": error_msg if error_msg else str(output)
            })
            
            # Only add formatted tool output to final response if show_output is True
            if tools.should_show_output(tool.function.name):
                final_response_parts.append(f"**{tool_emoji} {pretty_name}:**\n{error_msg if error_msg else str(output)}")

        # Get the agent to interpret all tool results together
        follow_up_messages = [
            {
                "role": "system",
                "content": "Review the tool outputs and provide a clear response to the user in markdown format. If there were any errors, explain them and suggest next steps. If it is a story property, offer to save it to the story object. If the user had you save any properties, suggest what properties they might want to save next. If the tool output doesn't satisfy the request, then try it again."
            },
            *messages,  # Original conversation
            *tool_outputs  # Tool results
        ]
        
        # Log the follow-up prompt
        st.session_state.debug_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": "follow_up_prompt",
            "model": AGENT_MODEL,
            "messages": follow_up_messages
        })
        
        follow_up_response = chat(
            AGENT_MODEL,
            messages=follow_up_messages,
            options=get_chat_options(follow_up_messages)
        )
        
        # Log the follow-up response
        st.session_state.debug_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": "follow_up_response",
            "model": AGENT_MODEL,
            "response": follow_up_response.model_dump()
        })
        
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

# Add near the top with other session state initializations
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []

# Add near the top with other session state initializations
if "show_changes_dialog" not in st.session_state:
    st.session_state.show_changes_dialog = False
if "changes_to_show" not in st.session_state:
    st.session_state.changes_to_show = None

st.title("📖 Story Chatbot")

# Create tabs
chat_tab, diffs_tab, story_tab, debug_tab = st.tabs([
    "💬 Assistant",
    "🔀 Changes",
    "🔍 Story Object",
    "🐛 Debug"
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

# Add the Debug tab content after the other tabs
with debug_tab:
    st.markdown("### Debug Logs")
    
    # Add buttons to clear logs and copy to clipboard
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Clear Logs", use_container_width=True):
            st.session_state.debug_logs = []
            st.rerun()
    
    # Display logs in an expandable container with syntax highlighting
    if st.session_state.debug_logs:
        for log in reversed(st.session_state.debug_logs):
            # Format the title based on log type
            title = f"{log['type']} - {log['timestamp']}"
            if log['type'] == "tool_call":
                title = f"🔧 Tool Call: {log['tool']} - {log['timestamp']}"
            elif log['type'] == "tool_output":
                title = f"📤 Tool Output: {log['tool']} - {log['timestamp']}"
            elif log['type'] == "agent_input":
                title = f"🤖 Agent Input - {log['timestamp']}"
            elif log['type'] == "agent_output":
                title = f"💬 Agent Output - {log['timestamp']}"
            elif log['type'] == "creative_input":
                title = f"✍️ Creative Input - {log['timestamp']}"
            elif log['type'] == "creative_output":
                title = f"📝 Creative Output - {log['timestamp']}"
            elif log['type'] == "follow_up_prompt":
                title = f"🔄 Follow-up Prompt - {log['timestamp']}"
            elif log['type'] == "follow_up_response":
                title = f"↩️ Follow-up Response - {log['timestamp']}"
            
            with st.expander(title, expanded=False):
                try:
                    st.code(json.dumps(log, indent=2), language="json")
                except Exception as e:
                    st.write(f"Error: {e}")
                    st.code(log)
    else:
        st.info("No debug logs available yet. Start a conversation to see the interactions.")

def show_changes_dialog():
    """Displays a dialog with recent changes."""
    st.dialog("Recent Changes")
    st.write(st.session_state.changes_to_show)

# Ensure this function is defined before it's called
if st.session_state.show_changes_dialog:
    show_changes_dialog()

