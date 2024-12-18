import streamlit as st
from plotomatic.project_manager import get_project_manager
from plotomatic.models.chat import Message, ChatSession
from plotomatic.components import view_diffs_and_manage_changes, selected_project_name, project_selector
from plotomatic.assistant.story_overview_assistant import StoryOverviewAssistant
from streamlit.logger import get_logger
import time
from plotomatic.assistant.states import AssistantState

# Get a logger instance
logger = get_logger('plotomatic')

# Let the user specify a chat name
chat_name = "title_plot_chat"

st.set_page_config(page_title="Story Chatbot", page_icon="📖", layout="wide")

# Initialize ProjectManager and load story
pm = get_project_manager()

# Check if project has changed and clear chat if needed
current_project = pm.get_current_project()
if "last_loaded_project" not in st.session_state or current_project != st.session_state.last_loaded_project:
    st.session_state.last_loaded_project = current_project
    st.rerun()

# Load story and chat session for current project
story = pm.load_story()

# If there is no story, redirect to the story creation page
if not story:
    st.switch_page("pages/00_Select_Project.py")

chat_session = pm.load_chat(chat_name)
messages = [msg.model_dump() for msg in chat_session.messages] if chat_session else []

selected_project_name()
project_selector()

def get_thinking_emoji():
    """Returns a cycling thinking emoji based on the current time."""
    emojis = ["💭", "🤔", "🧠", "💡", "🧐"]
    return emojis[int(time.time()) % len(emojis)]

def get_tool_status_emoji(state: AssistantState, is_current: bool = False) -> str:
    """Returns an emoji based on the tool's execution state.
    
    Args:
        state (AssistantState): The current state
        is_current (bool): Whether this is the currently executing tool
    """
    if is_current:
        return "⚡"  # Currently executing
    elif state == AssistantState.PROCESSING_TOOL_CALLS:
        return "⏳"  # Waiting to execute
    elif state == AssistantState.PROCESSING_TOOL_OUTPUTS:
        return "✅"  # Done
    return "🔄"  # Default

def chat_agent(messages):
    project_path = pm.get_current_project_path()
    if not project_path:
        st.error("No project selected")
        return
    
    # Load or create assistant for this project
    assistant = StoryOverviewAssistant.load_for_project(project_path)
    assistant.story = story
    
    # Update assistant's chat session with current messages
    assistant.chat_session.messages = [Message(**m) for m in messages]
    
    # Get the last user message
    last_message = messages[-1]
    if last_message["role"] == "user":
        # Create or load current interaction
        if not chat_session.current_interaction:
            chat_session.current_interaction = {
                "user_message": last_message["content"],
                "tool_calls": [],
                "states": [],
                "final_response": None
            }
        
        # Send the message to the assistant if we haven't already
        if not chat_session.current_interaction["states"]:
            assistant.send_message(last_message["content"])
        
        # Get current state and add to states if new
        current_state = assistant.state
        if not chat_session.current_interaction["states"] or chat_session.current_interaction["states"][-1] != current_state:
            chat_session.current_interaction["states"].append(current_state)
        
        # Run one iteration if not waiting for user
        if current_state != AssistantState.WAITING_USER_INPUT:
            # Run one iteration
            assistant.run()
            
            # Check for streaming content
            stream = assistant.get_current_stream()
            if stream:
                with st.chat_message("assistant"):
                    content = st.write_stream(stream)
                    # Store the streamed content
                    if content:
                        messages.append({
                            "role": "assistant", 
                            "content": content,
                            "show_user": True
                        })
                        # Save chat session
                        chat_session = ChatSession(messages=[Message(**m) for m in messages])
                        pm.save_chat(chat_name, chat_session)
            
            # If we have new tool calls, record them
            if assistant.tool_calls:
                for tool_call in assistant.tool_calls:
                    tool_info = {
                        "name": tool_call.name,
                        "emoji": assistant.get_tool_emoji(tool_call.name),
                        "arguments": tool_call.arguments,
                        "state": current_state
                    }
                    if tool_info not in chat_session.current_interaction["tool_calls"]:
                        chat_session.current_interaction["tool_calls"].append(tool_info)
            
            # Save any story changes
            if assistant.story != story:
                pm.save_story(assistant.story)
            
            # Save current state
            pm.save_chat(chat_name, chat_session)
            
            # Trigger a rerun to continue processing
            st.rerun()
        
        # If we're done processing, add the final response
        if current_state == AssistantState.WAITING_USER_INPUT:
            response = assistant.get_last_response()
            if response and not assistant.get_current_stream():  # Only if not streaming
                chat_session.current_interaction["final_response"] = response["content"]
                
                # Add the interaction record to messages
                messages.append({
                    "role": "assistant",
                    "content": response["content"],
                    "interaction": chat_session.current_interaction
                })
                
                # Clear current interaction
                chat_session.current_interaction = None
                
                # Save the updated chat session
                chat_session = ChatSession(messages=[Message(**m) for m in messages])
                pm.save_chat(chat_name, chat_session)
                
                # Trigger a rerun to update the UI
                st.rerun()

def process_message():
    if prompt := st.session_state.chat_input:
        # Add user message to chat history
        messages.append({"role": "user", "content": prompt})
        
        # Save chat session with new user message
        chat_session = ChatSession(messages=[Message(**m) for m in messages])
        pm.save_chat(chat_name, chat_session)
        
        # Process the message with the assistant
        chat_agent(messages)

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
                st.rerun()
        with col2:
            if st.button("No, cancel", use_container_width=True):
                st.rerun()

    # Delete chat button
    if st.button("🗑️ Delete Chat", 
                type="secondary", 
                help="Clear the entire chat history",
                disabled=not messages):
        delete_confirmation()

    chat_container = st.container(border=True)
    with chat_container:
        # Display all messages that should be shown
        for msg in messages:
            if msg.get("show_user", False):  # Default to False if not specified
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
                    # If this message has an interaction record, show the tool calls
                    if msg.get("interaction"):
                        interaction = msg["interaction"]
                        if interaction["tool_calls"]:
                            with st.expander("🔧 Tool Calls"):
                                for tool in interaction["tool_calls"]:
                                    # Check if this is the currently executing tool
                                    is_current = (
                                        chat_session.current_interaction and 
                                        assistant.get_current_tool() and
                                        assistant.get_current_tool().name == tool["name"]
                                    )
                                    status_emoji = get_tool_status_emoji(tool["state"], is_current)
                                    
                                    # Show current execution status if available
                                    status_text = assistant.get_current_tool_status() if is_current else ""
                                    st.markdown(f"{tool['emoji']} {tool['name']}: {status_emoji} {status_text}")
                                    
                                    with st.status(f"Arguments", expanded=False):
                                        st.json(tool["arguments"])

        # Show thinking status if processing
        if chat_session.current_interaction:
            with st.status(f"{get_thinking_emoji()} Processing", expanded=True) as status:
                st.write("Processing your message...")
                # Show current tool calls
                for tool in chat_session.current_interaction["tool_calls"]:
                    # Check if this is the currently executing tool
                    is_current = (
                        assistant.get_current_tool() and
                        assistant.get_current_tool().name == tool["name"]
                    )
                    status_emoji = get_tool_status_emoji(tool["state"], is_current)
                    st.markdown(f"{tool['emoji']} {tool['name']}: {status_emoji}")

        # Chat input
        st.chat_input(
            "Ask a question",
            key="chat_input",
            on_submit=process_message,
            disabled=chat_session.current_interaction is not None  # Disable while processing
        )

# Diffs Tab
with diffs_tab:
    view_diffs_and_manage_changes()

# Story Data Tab
with story_tab:
    st.json(story)

