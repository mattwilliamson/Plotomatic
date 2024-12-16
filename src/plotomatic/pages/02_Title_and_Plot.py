import streamlit as st
from plotomatic.project_manager import get_project_manager
from plotomatic.models.chat import Message, ChatSession
from plotomatic.components import view_diffs_and_manage_changes, selected_project_name, project_selector
from plotomatic.assistant.story_overview_assistant import StoryOverviewAssistant
from streamlit.logger import get_logger
import time

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
    assistant.save_state()
    
    # Get the last user message
    last_message = messages[-1]
    if last_message["role"] == "user":
        # Send the message to the assistant
        assistant.send_message(last_message["content"])
        
        # Run the assistant's processing loop
        assistant.run()
        
        # Save any story changes
        if assistant.story != story:
            pm.save_story(assistant.story)
        
        # Get the assistant's response and add it to messages
        response = assistant.get_last_response()
        if response:
            messages.append({
                "role": "assistant",
                "content": response["content"],
                "tool_calls": response.get("tool_calls", [])
            })
            
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
        # Display all messages
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                if msg.get("tool_calls"):
                    for tool_call in msg["tool_calls"]:
                        if tool_call["function"]["name"] == "show_user_options":
                            args = tool_call["function"]["arguments"]
                            st.markdown(f"**{args['prompt']}**")
                            
                            cols = st.columns(max(1, len(args['choices'])))
                            for i, choice in enumerate(args['choices']):
                                with cols[i]:
                                    if st.button(str(choice), use_container_width=True):
                                        messages.append({
                                            "role": "user",
                                            "content": str(choice)
                                        })
                                        chat_session = ChatSession(messages=[Message(**m) for m in messages])
                                        pm.save_chat(chat_name, chat_session)
                                        chat_agent(messages)

        # Show thinking status if the last message was from the user
        if messages and messages[-1]["role"] == "user":
            with st.status(f"{get_thinking_emoji()} Thinking...", expanded=True, state="running") as status:
                st.write("Processing your message...")
        else:
            # Show ready status
            with st.status("Ready for your message", state="complete") as status:
                pass

        # Chat input
        st.chat_input(
            "Ask a question",
            key="chat_input",
            on_submit=process_message,
            disabled=messages and messages[-1]["role"] == "user"  # Disable input while processing
        )

# Diffs Tab
with diffs_tab:
    view_diffs_and_manage_changes()

# Story Data Tab
with story_tab:
    st.json(story)

