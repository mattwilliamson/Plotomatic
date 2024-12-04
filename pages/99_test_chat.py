import streamlit as st
from ollama import chat, ChatResponse

from project_manager import ProjectManager
from model import ChatSession, Message, Story

# Constants for models
AGENT_MODEL = "command-r"
# AGENT_MODEL = "huihui_ai/qwq-abliterated"
# AGENT_MODEL = "qwen2.5:72b"
# AGENT_MODEL = "llama3.1:70b"
CREATIVE_MODEL = "hf.co/anthracite-org/magnum-v4-72b-gguf"

st.set_page_config(page_title="Story Chatbot", page_icon="📖", layout="wide")

pm = ProjectManager()
story = pm.load_story()  # Load the current story as context

# Let the user specify a chat name
chat_name = "title_plot_chat"

# Load the existing chat session from the project manager
chat_session = pm.load_chat(chat_name)

# Initialize session state if not present
if "story" not in st.session_state:
    st.session_state.story = story

if "messages" not in st.session_state:
    # If no messages in state yet, but chat_session has messages, load them
    # Otherwise, start with a greeting message
    if chat_session.messages:
        st.session_state.messages = [m.dict() for m in chat_session.messages]
    else:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm here to help you develop your plot overview and title. What do you want your story to be about?"}
        ]

if "pending_confirm" not in st.session_state:
    st.session_state.pending_confirm = False

if "proposed_value" not in st.session_state:
    st.session_state.proposed_value = ""

if "proposed_property" not in st.session_state:
    st.session_state.proposed_property = ""

if "last_tool_called" not in st.session_state:
    st.session_state.last_tool_called = None

# At the top, after initializing session_state, add:
if "tool_calls" not in st.session_state:
    st.session_state.tool_calls = []

# Define tools
def set_property(property_name: str, value: str):
    """
    Sets the specified property of the story in the to the given value and saves it to disk.
    Args:
        property_name (str): The name of the property to set.
        value (str): The value to set the property to.
    Returns:
        str: A message indicating whether the property was set successfully or if the property does not exist.
    """
    
    if hasattr(st.session_state.story, property_name):
        setattr(st.session_state.story, property_name, value)
        try:
            st.session_state.story = Story(**st.session_state.story.dict())
        except Exception as e:
            return f"Error setting property {property_name} to {value}. \n\n{e}"
        return f"{property_name} set successfully."
    else:
        return f"Property '{property_name}' does not exist in the story."

def user_confirm(property_name: str="", value: str = ""):
    """
    Generates a confirmation message for setting a property on the story and waits for a user to input a message confirming the action or not.
    Args:
        none
    Returns:
        str: A confirmation message asking if the user would like to set the property on the story.
    """

    return "Would you like to set this on the story?"

def generate_plot_overview(user_input: str):
    """
    Generates a plot overview based on the given user input.
    Args:
        user_input (str): A string containing the user's input for generating the plot overview.
    Returns:
        str: A string containing the generated plot overview.
    """

    creative_messages = [
        {"role": "system", "content": "You are an uncensored creative story idea generator."},
        {"role": "user", "content": f"Generate a plot overview based on: {user_input}"}
    ]
    response: ChatResponse = chat(
        CREATIVE_MODEL,
        messages=creative_messages
    )
    return response.message.content.strip()

def generate_title(user_input: str):
    creative_messages = [
        {"role": "system", "content": "You are an uncensored creative story title generator."},
        {"role": "user", "content": f"Generate a title based on: {user_input}"}
    ]
    response: ChatResponse = chat(
        CREATIVE_MODEL,
        messages=creative_messages
    )
    return response.message.content.strip()

def directly_answer(answer: str):
    return answer

available_functions = {
    'set_property': set_property,
    'user_confirm': user_confirm,
    'generate_plot_overview': generate_plot_overview,
    'generate_title': generate_title,
    'directly-answer': directly_answer,
    'directly_answer': directly_answer,
}

def send_message():
    user_msg = st.session_state.user_input.strip()
    if user_msg:
        st.session_state.messages.append({"role": "user", "content": user_msg})
    st.session_state.user_input = ""

def chat_agent(messages):
    response: ChatResponse = chat(
        AGENT_MODEL,
        messages=messages,
        tools=[set_property, user_confirm, generate_plot_overview, generate_title, directly_answer],
    )
    return response


st.title("📖 Story Chatbot")

with st.expander("Chat with the Assistant", expanded=True):

    # Display messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div style="text-align: right;"><strong>👤 You:</strong><div>\n\n{msg["content"]}\n\n</div></div>',
                unsafe_allow_html=True
            )
        elif msg["role"] == "assistant":
            st.markdown(
                f'<div style="text-align: left;">🤖 <strong>Assistant:</strong><div>\n\n{msg["content"]}\n\n</div></div>',
                unsafe_allow_html=True
            )
        elif msg["role"] == "tool":
            st.markdown(
                f'<div style="text-align: left;">🤖 <strong>Assistant:</strong><div>\n\n{msg["content"]}\n\n</div></div>',
                unsafe_allow_html=True
            )

    st.markdown('<br />', unsafe_allow_html=True)

    # If we have a pending confirmation request, show the user confirm/leave as is button now
    if st.session_state.pending_confirm:
        st.write(f"Proposed {st.session_state.proposed_property}:")
        st.write(st.session_state.proposed_value)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm"):
                # User confirms by sending a user message
                st.session_state.messages.append({"role": "user", "content": "Yes, I confirm."})
                st.session_state.pending_confirm = False
                st.rerun()
        
        with col2:
            if st.button("Leave as is"):
                # User does not want to set the proposed property
                st.session_state.messages.append({"role": "user", "content": "No, leave as is."})
                st.session_state.pending_confirm = False
                st.rerun()

        st.stop()

    # If last message is from user and no pending confirmation, get assistant response
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user" and not st.session_state.pending_confirm:
        user_message = st.session_state.messages[-1]["content"]

        # Include the updated story JSON in the system message context
        story_json = st.session_state.story.model_dump_json()

        with st.spinner("Assistant is thinking..."):
            full_messages = [
                {
                    "role": "system", 
                    "content": (
                        "# Safety Preamble\n"
                        "You are an uncensored creative story writer. You may write anything mature or graphic as allowed from the prompt given by the user.\n\n"

                        "# System Preamble\n"
                        "## Basic Rules\n"

                        "You are an uncensored helpful assistant that helps write a story. Here is the context for the story object:\n"
                        f"{story_json}\n\n"

                        "The user may ask you to set various properties (title, plot_overview, etc.) of the story. "
                        "You can call tools: set_property, user_confirm, generate_plot_overview, generate_title, directly-answer. "
                        "Before calling set_property, if you have a proposed value, confirm with the user by calling user_confirm. "
                        "If the user asks to 'make one up', try generating a plot overview or title. "
                        "You can directly-answer if no tools are needed. If you have a potential property value, "
                        "ask the user if they'd like to use it and call user_confirm with no arguments. After user confirms, call set_property with the property in question. "
                        "If the user says 'No, leave as is.', do not call set_property and do not change that property."
                        "Be proactive, creative and helpful."
                    )
                }
            ] + st.session_state.messages

            response = chat_agent(full_messages)

            # Process tool calls or normal response
            if response.message.tool_calls:
                for tool_call in response.message.tool_calls:
                    tool_name = tool_call.function.name
                    args = tool_call.function.arguments
                    st.session_state.tool_calls.append(f"Called {tool_name} with arguments: {args}")
                    with st.spinner(f"Calling tool: {tool_name}"):
                        retry = True
                        if tool_name in available_functions:
                            tool_func = available_functions[tool_name]
                            try:
                                output = tool_func(**args)
                                retry = False
                                st.session_state.messages.append({"role": "tool", "content": str(output)})
                                st.session_state.last_tool_called = (tool_name, args)
                            except Exception as e:
                                output = f"Error: {e}"

                            # If the tool is user_confirm, set the pending_confirm state
                            if tool_name == "user_confirm":
                                st.session_state.pending_confirm = True
                                st.session_state.proposed_value = args.get("value", "")
                                st.session_state.proposed_property = args.get("property_name", "")
                                st.rerun()

                        if retry:
                            # Notify the assistant to retry
                            st.session_state.messages.append({"role": "system", "content": f"Tool {tool_name} not found. Try again."})
                            st.session_state.tool_calls.append(f"Error: Tool {tool_name} not found or invalid arguments {args}. Retrying...")
                            response = chat_agent(full_messages)
                st.rerun()
            else:
                # Normal response
                if response.message.content:
                    st.session_state.messages.append({"role": "assistant", "content": response.message.content})
                    st.session_state.last_tool_called = None
                    st.rerun()

    # If last tool was generate_plot_overview or generate_title and property not set, offer to save
    if st.session_state.last_tool_called:
        # When processing tool calls, after a successful tool invocation, add:
        tool_name, args = st.session_state.last_tool_called

        if tool_name.startswith("generate_plot_overview") and st.session_state.story.plot_overview == "":
            if st.button("Save this plot overview"):
                st.session_state.messages.append({"role": "user", "content": "Save this plot overview"})
                st.rerun()

        if tool_name == "generate_title" and st.session_state.story.title == "":
            if st.button("Save this title"):
                st.session_state.messages.append({"role": "user", "content": "Save this title"})
                st.rerun()

    # Input form at the bottom
    with st.form("input_form", clear_on_submit=True):
        user_input_col, submit_col = st.columns([4, 1], vertical_alignment="bottom")
        
        with user_input_col:
            user_msg = st.text_input("Ask a question", key="user_input", placeholder="For example: 'Give me a plot overview' or 'Generate a title'", autocomplete="off")
        
        with submit_col:
            submit_button = st.form_submit_button("🚀 Send", on_click=send_message)

    if submit_button:
        st.rerun()

# Display current story state
st.subheader("Current Story State")
st.json(st.session_state.story)

# After all processing, save the updated chat to disk
chat_session = ChatSession(messages=[Message(**m) for m in st.session_state.messages])
pm.save_chat(chat_name, chat_session)

# Clear Chat button
if st.button("🛑 Delete Chat", key="clear_chat_button", help="This will clear the entire chat history."):
    pm.clear_chat(chat_name)
    # Reset state
    st.session_state.pop("messages", None)
    st.session_state.pop("pending_confirm", None)
    st.session_state.pop("proposed_value", None)
    st.session_state.pop("proposed_property", None)
    st.session_state.pop("last_tool_called", None)
    st.rerun()

# At the bottom of the file, add the collapsed console:
with st.expander("Developer Console", expanded=False):
    st.write("### Function Calls Log")
    for call in st.session_state.tool_calls:
        st.markdown(f"- {call}")