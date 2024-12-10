import streamlit as st
from plotomatic.llm_models import ollama_client
from project_manager import ProjectManager
from models.story import Story
from models.chat import Message, ChatSession
from plotomatic.components import view_diffs_and_manage_changes, selected_project_name, project_selector
from plotomatic.git_utils import get_repo, get_changed_files, commit_file
from typing import Type
from pydantic import BaseModel
import json
from datetime import datetime
from streamlit import dialog
import time
from plotomatic.chat_tools import tools, save_current_state, format_diff
from plotomatic.llm_models import BASE_MODELS, AGENT_MODEL, CREATIVE_MODEL, AGENT_SYSTEM_PROMPT, CREATIVE_SYSTEM_PROMPT, create_model, ensure_base_models
import logging
from streamlit.logger import get_logger
import random

# Get a logger instance
logger = get_logger('plotomatic')

# Let the user specify a chat name
chat_name = "title_plot_chat"

# Ensure models exist when the app starts
ensure_base_models()

st.set_page_config(page_title="Story Chatbot", page_icon="📖", layout="wide")

# Initialize ProjectManager and load story
pm = ProjectManager()

# Add near the top with other session state initializations
if "last_loaded_project" not in st.session_state:
    st.session_state.last_loaded_project = None

# Check if project has changed
current_project = pm.get_current_project()
if current_project != st.session_state.last_loaded_project:
    # Clear existing chat state
    if "messages" in st.session_state:
        del st.session_state.messages
    if "story" in st.session_state:
        del st.session_state.story
    st.session_state.last_loaded_project = current_project
    # Force a rerun to reload with new project
    st.rerun()

# Load story and chat session for current project
story = pm.load_story()

# If there is no story, redirect to the story creation page
if not story:
    st.switch_page("pages/00_Select_Project.py")

chat_session = pm.load_chat(chat_name)

# Initialize session states after potential reload
if "story" not in st.session_state:
    st.session_state.story = story

few_shots = [
    # Fist show_user_options
    {
        "role": "assistant", 
        "content": """I'm ready when you are.""", 
        "tool_calls": [{
            "function": {
                "name": "show_user_options",
                "arguments": {
                    "prompt": "Are you ready to start?",
                    "options": ["I'm ready!", "Not yet."]
                }
            }
        }]
    },

    # User says they are ready
    {
        "role": "user",
        "content": "I'm ready!"
    },

    # Show an example of how to prompt and save a property
    {
        "role": "assistant", 
        "content": "I see there is a title set already.", 
        "tool_calls": [{
                "function": {
                    "name": "show_user_options",
                    "arguments": {
                        "prompt": "Would you like me to erase the title and start over?",
                        "options": ["Yes, erase it", "No, keep it"]
                    }
                }
            }
        ]
    },

    # User says they want to start over
    {
        "role": "user",
        "content": "Yes, erase it"
    },

    # Set the title to an empty string
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [{
            "function": {
                "name": "set_property",
                "arguments": {
                    "property_name": "title",
                    "value": ""
                }
            }
        }]
    },

    # Ask how they want to start
    {"role": "assistant", "content": """Your title is now empty. Let's do this.""", 
        "tool_calls": [{
                "function": {
                    "name": "show_user_options",
                    "arguments": {
                        "prompt": "How do you want to start?",
                        "options": ["Ask me some questions", "Make up a story"]
                    }
                }
            }
        ]
    },

    # User says they want to ask questions
    {
        "role": "user",
        "content": "Ask me some questions"
    },
]

if "messages" not in st.session_state:
    # If no messages in state yet, but chat_session has messages, load them
    # Otherwise, start with a greeting message
    if chat_session and chat_session.messages:
        st.session_state.messages = [m.model_dump() for m in chat_session.messages]
    else:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": """**Hello! 👋** 
                
I'm your Plotomatic story development assistant. 
I'll help you build your story piece by piece.
                
The tabs above will help you see the:
- 💬 **Assistant** - hey, that's me!
- 🔀 **Changes** - review the changes you've made to the story
- 🔍 **Story Object** - inspect the current state of the story overview
- 🐛 **Debug** - advanced tracing information

Do you have a story idea in mind? 

Tell me about it or I'll make one up.""",
    },
]

        # # Check if author is set
        # if st.session_state.story.author:
        #                 # Ask the first question
        #     {
        #         "role": "assistant",
        #         "content": "Who's name should I set as the author?"
        #     },
        #     few_shots.append({"role": "user", "content": story.author})
        #     few_shots.append({"role": "assistant", "content": "Do you have an idea in mind? Tell me about it or I'll make one up."})


selected_project_name()
project_selector()

if 'pm' not in st.session_state:
    st.session_state.pm = pm

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

# Now that messages are initialized, we can set up the hash tracking
if "original_story_hash" not in st.session_state:
    st.session_state.original_story_hash = hash(st.session_state.story.model_dump_json())

if "original_chat_hash" not in st.session_state:
    st.session_state.original_chat_hash = hash(str([m["content"] for m in st.session_state.messages]))

# Replace the static chat_options with a function
def get_chat_options(messages):
    # Estimate tokens by counting characters and dividing by 4
    # Include a safety margin multiplier of 1.2
    estimated_tokens = sum(len(str(m)) for m in messages) // 4 * 1.4
    num_predict = 5000  # Keep the same prediction length
    # https://github.com/ollama/ollama/blob/main/docs/modelfile.md#valid-parameters-and-values
    # https://github.com/ollama/ollama/blob/main/docs/api.md

    return {
        # 'num_ctx': int(estimated_tokens + num_predict),
        'num_ctx': 6000,
        'num_predict': num_predict,
        "temperature": 0.5,             # 0.2 to 0.4    - A lower temperature ensures that responses are more deterministic and coherent. This helps the assistant provide clear and reliable answers without unnecessary creativity that could lead to confusion.
        # "top_p": 0.4,                   # 0.3 to 0.5    - A smaller top_k value restricts the assistant to a few of the highest probability tokens at each step. This focus on the most likely options helps maintain coherence and ensures that the assistant's responses are aligned with user expectations, particularly important in structured tasks like function calls.
        # "top_k": 7,                     # 5 and 10      - A lower top_k focuses on the most probable responses, enhancing clarity while still allowing for some diversity in word choice.
        # "mirostat_tau": 0.8,        # 1.0 to 2.0    - Setting this parameter within this range can help balance coherence and diversity in outputs, allowing for adjustments based on user feedback while keeping responses focused.
        # "mirostat_eta": 0.6,        # 0.5 to 1.0    - A moderate learning rate allows the model to adjust its outputs based on previous interactions, enhancing its ability to follow function calls accurately while maintaining coherence.
        "mirostat": 1,              # 0 or 1        - Enabling Mirostat allows for dynamic control over the perplexity of the generated text, which helps in avoiding both "boredom traps" (excessive repetitions) and "confusion traps" (incoherence). This is particularly useful for applications requiring coherent outputs, such as function calls in an assistant. By maintaining an appropriate level of perplexity, Mirostat can help ensure that the generated text remains relevant and consistent.
        # "tfs_z": 0.3,               # 0.3 to 0.5    - TFS (Top-p Sampling with Temperature) z values in this range help control the diversity of the output while keeping it coherent. A lower value encourages more deterministic outputs, which is essential for an assistant focused on function calls.
        # "typical_p": 0.5,           # 0.5 to 0.7    - This range allows the model to generate responses that are typical or expected, enhancing coherence in its outputs. A typical_p value around 0.5 to 0.7 helps ensure that the assistant's responses are relevant and aligned with user queries.
        # "repeat_penalty": 1.0,          # 0.0 to 0.2    - A very low repeat penalty allows the model to repeat necessary information when relevant, which is crucial for function calls and maintaining context.
        # "presence_penalty": 0.3,        # 0.0 to 0.3    - Keeping this low ensures that the assistant can refer back to previously mentioned concepts or topics, which is helpful in maintaining a coherent conversation.
        # "frequency_penalty": 0.3,       # 0.0 to 0.3    - A low frequency penalty allows for the use of common phrases and terms, which can enhance clarity and make the assistant's responses more relatable and understandable.
        # "min_p": 0.1,               # 0.0 to 0.1    - Setting min_p to a very low value allows for a broader range of responses while still maintaining coherence. This ensures that the assistant can explore options without being overly constrained, which is useful for function calls.
        # "repeat_last_n": 33,        # 10 to 20      - Setting repeat_last_n to a lower value helps prevent excessive repetition in responses, which can detract from coherence. This range allows the model to maintain some context from previous interactions without becoming too repetitive.
        'seed': random.randint(0, 1000000),
    }
    # Defaults
    # "num_keep": 5,
    # "seed": 42,
    # "num_predict": 100,
    # "top_k": 20,
    # "top_p": 0.9,
    # "min_p": 0.0,
    # "tfs_z": 0.5,
    # "typical_p": 0.7,
    # "repeat_last_n": 33,
    # "temperature": 0.8,
    # "repeat_penalty": 1.2,
    # "presence_penalty": 1.5,
    # "frequency_penalty": 1.0,
    # "mirostat": 1,
    # "mirostat_tau": 0.8,
    # "mirostat_eta": 0.6,
    # "penalize_newline": true,
    # "stop": ["\n", "user:"],
    # "numa": false,
    # "num_ctx": 1024,
    # "num_batch": 2,
    # "num_gpu": 1,
    # "main_gpu": 0,
    # "low_vram": false,
    # "vocab_only": false,
    # "use_mmap": true,
    # "use_mlock": false,
    # "num_thread": 8
def execute_tool(tool_name, arguments):
    """Executes a tool function and returns the output and any error message."""
    logger.info(f"execute_tool: {tool_name} {arguments}")
    function_to_call = tools.get_tool(tool_name)

    if function_to_call:
        try:
            output = function_to_call(**arguments)
            logger.info(f"execute_tool output: {output}")
            return output, None
        except Exception as e:
            logger.info(f"execute_tool error: {e}")
            return None, f"Error executing {tool_name}: {str(e)}"
    else:
        logger.info(f"Tool {tool_name} not found or invalid arguments")
        return None, f"Tool {tool_name} not found or invalid arguments"

def chat_agent(messages):
    # Get current story state
    story = st.session_state.story
    
    # Create a filtered story state for the context
    story_dict = story.model_dump()
    story_dict.pop('acts', None)
    story_dict.pop('characters', None)
    story_dict.pop('cover_design', None)
    
    # Generate model documentation
    model_docs = generate_model_docs(Story)
    
    logger.info("Starting chat agent")
    
    # Construct full messages with enhanced system context
    full_messages = [
        {
            "role": "system", 
            "content": AGENT_SYSTEM_PROMPT + f"""# User Preamble

## Task and Context

You are responsible for helping the user set the title, plot_overview, author and other high level properties of the story.
You are only allowed to set the top level properties in the story object.
You may not modify the acts or characters properties in this stage. There is another page for each of those.
You may, however inject a small number of characters or other details into the plot_overview by appending to it in order to help bootstrap the story.
If a user asks you to make up a story, just start with the plot_overview and then ask the user if they want to save it by calling set_property with the property "plot_overview". You may also set the title property if it is blank and ask to save it.

### Interface Information:
- The "Changes" tab shows updates to the story since the last git commit and allows you to commit them to a new version in the revision history. Any time you make changes to the story, tell the user to check the changes tab to see what you've done.
- The "Story Object" tab displays the current state of all story fields
- The "Console" tab shows technical details for debugging

### Story Creation Process (you are responsible for just General Information / Step 1):
1. **General Information**: Start by setting general information about the story, such as the author, title, and plot overview. These are the thing you will be setting.
2. **Characters**: Move to the next page to add and develop characters, including their arcs and relationships. Only offer this if the story overview details are complete, like a title and plot. You will not be setting characters here.
3. **Acts, Chapters, and Scenes**: Proceed to generate the structure of the story by creating acts, chapters, and scenes. Only offer this if the story overview details are complete, like a title and plot. You will not be setting acts, chapters, or scenes here.
4. **Narrative Content**: Create the narrative content for each scene, detailing the events and dialogues.
5. **Cover Art**: Generate cover art for the story, including the front and back covers.
6. **PDF Generation**: Compile the text into a PDF and create a separate PDF for the cover.

### Important Rules:
 - If tool calls depend on each other, you may use a placeholder in the final response to indicate where the output of the dependent tool should go. Replace the placeholder with the actual output of the dependent tool as soon as it is available.
 - Use as many tools as you need.
 - The final response to the user must be a markdown formatted response
 - show_user_options will end the conversation

## Style Guide
Output to the user can be formatted as markdown. Make sure to output actual values and not placeholders.

### Story Model Structure:
{model_docs}

### Project name:
{current_project}

### Current story context (excluding acts and characters): 
{json.dumps(story_dict, indent=2)}

## Important:
Don't call set_property without letting the user know you are doing it and make sure it is a valid property name.
**Be extra cautious about calling set_property with destructive operations like setting a property to an empty string or None**
Do not use any placeholders like [Insert generated text here] or [Generated text] or <story_text> ever.
Only call set_property if the new value is different from the old value.
If set_property is dependent on a previous creative_write, then you must call creative_write first.

## Tool Output Validation Rules
After each tool call, you MUST:
 - Validate that the output matches what you needed
 - If the output is not satisfactory, call it again with a more specific prompt
 - If it seems like the output is good, then ask the user if they approve or solicit a change with a show_user_options tool call e.g. "Would you like to save this title?" or "Would you like to try another plot overview?"

Remember: Quality is more important than speed. Don't hesitate to retry tool calls if the output isn't exactly what you need.

"""
        },
        *few_shots,
        *messages
    ]
    
    # Log the agent input
    st.session_state.debug_logs.append({
        "timestamp": datetime.now().isoformat(),
        "type": "agent_input",
        "model": AGENT_MODEL,
        "messages": full_messages
    })
    
    # Initialize variables for the loop
    tool_outputs = []
    final_response_parts = []
    continue_processing = True
    max_iterations = 10  # Prevent infinite loops
    iteration = 0
    
    while continue_processing and iteration < max_iterations:
        iteration += 1
        logger.info(f"ChatAgent Iteration {iteration}")
        
        # Get response from the model
        response = ollama_client.chat(
            AGENT_MODEL,
            messages= [*full_messages, *tool_outputs],  # Include previous tool outputs
            tools=list(tools.available_functions.values()),
            options=get_chat_options(full_messages),
            keep_alive="1h", 
        )

        # Log the agent output
        st.session_state.debug_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": "agent_output",
            "model": AGENT_MODEL,
            "response": response.model_dump()
        })

        # Check if there are no tool calls or only terminal tools
        if not response.message.tool_calls:
            logger.info("No tool calls")
            continue_processing = False
        else:
            # Check if only terminal tools remain
            terminal_tools = {'show_user_options',}
            remaining_tools = {tool.function.name for tool in response.message.tool_calls}
            logger.info(f"Remaining tools: {remaining_tools}")
            if remaining_tools.issubset(terminal_tools):
                logger.info("Only terminal tools remain")
                continue_processing = False

        # Process tool calls if any
        if response.message.tool_calls:
            for tool in response.message.tool_calls:
                # Get tool metadata
                tool_emoji = tools.get_emoji(tool.function.name)
                tool_metadata = tools.get_metadata(tool.function.name)
                pretty_name = tool_metadata.get('pretty_name', tool.function.name)
                
                logger.info(f"Tool: {tool.function.name}")
                logger.info(f"Tool Arguments: {tool.function.arguments}")
                
                # Format arguments for display
                args_str = ', '.join(f'{k}="{v}"' for k, v in tool.function.arguments.items())
                
                status.update(label=f"Running Tool...")
                st.write(f"{tool_emoji} Tool: **{pretty_name}**")

                # Log tool input
                st.session_state.debug_logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "tool_input",
                    "tool": tool.function.name,
                    "input": str(args_str)
                })
                
                # Execute the tool function
                output, error_msg = execute_tool(tool.function.name, tool.function.arguments)
                
                st.spinner(f"🧠 Processing tool output")
                
                logger.info(f"Tool Output: {output}")
                if error_msg:
                    logger.info(f"Error Message: {error_msg}")
                
                # Log tool output
                st.session_state.debug_logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "tool_output",
                    "tool": tool.function.name,
                    "output": str(output),
                    "error": error_msg
                })
                
                # Add tool result to collection for LLM context with validation reminder
                tool_outputs.append({
                    "role": "tool",
                    "name": tool.function.name,
                    "content": f"""# Tool Results

## Tool: {tool.function.name}

## Parameters: {args_str}

## Output: 

{error_msg if error_msg else str(output)}
"""
                })

                tool_outputs.append({
                    "role": "user",
                    "name": tool.function.name,
                    "content": f"""If any tool outputs are not exactly what you needed, try it again. 
If it seems good, then you can ask the user if they approve or solicit a change with a show_user_options tool call.
Show the user exactly what properties and values you intend to set.
Confirm with the user using show_user_options that they approve of the values you are setting. 

Give your final response in markdown format to the user if you can. Otherwise get clarification from the user or execute tools to gather more information.
"""})
                
                # TODO: Set all properties we have info for

                # Get the agent to interpret all tool results together
                status.update(label=f"💭 Reviewing tool outputs...")
                st.write(f"💭 Reviewing tool outputs...")
                logger.info(f"Reviewing tool outputs...")

                # TODO: Might need to reset tools once final response is generated
                
                # Only add formatted tool output to final response if show_output is True
                if tools.should_show_output(tool.function.name):
                    final_response_parts.append(f"**{tool_emoji} {pretty_name}:**\n{error_msg if error_msg else str(output)}")

        # Add the final response if we're stopping
        if not continue_processing and response.message.content:
            logger.info(f"Adding final response to messages...")
            logger.info(f"Final response: {response.message.content}")

            message_data = {
                "role": "assistant",
                "content": response.message.content
            }
            
            # Add tool calls if present
            if response.message.tool_calls:
                message_data["tool_calls"] = [
                    {"function": tool.function.model_dump()} 
                    for tool in response.message.tool_calls
                ]
            
            st.session_state.messages.append(message_data)
            
            # Save the chat session
            logger.info(f"Saving chat session...")
            chat_session = ChatSession(messages=[Message(**m) for m in st.session_state.messages])
            st.session_state.pm.save_chat(chat_name, chat_session)

    # If we hit max iterations, add a warning
    if iteration >= max_iterations:
        logger.info("Maximum number of tool call iterations reached")
        st.warning("Maximum number of tool call iterations reached")
    
    # Set processing to false since we're done
    st.session_state.processing = False
    
    # Force a rerun to update the UI
    logger.info(f"chat_agent rerun")
    st.rerun()
    
    return response

def process_message():
    """Process the message when the user hits enter or clicks send."""
    if prompt := st.session_state.chat_input:
        logger.info(f"Processing message: {prompt}")
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
        # if str(field.annotation).startswith("typing.Optional"):
        #     field_type = f"Optional[{field_type.replace('Optional[', '').replace(']', '')}]"
        
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
        logger.info(f"User input: {prompt}")
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
        for i, msg in enumerate(st.session_state.messages):
            logger.info(f"chat_container displaying Message {i}: {msg}")

            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # Check if this is the last assistant message and has show_user_options tool calls
                is_last_assistant = (msg["role"] == "assistant" and 
                                   i == len(st.session_state.messages) - 1)
                
                logger.info(f"is_last_assistant: {is_last_assistant}")
                
                if is_last_assistant and msg.get("tool_calls"):
                    # Look for show_user_options tool calls
                    for tool_call in msg["tool_calls"]:
                        logger.info(f"chat_container tool_call: {tool_call}")
                        
                        if tool_call["function"]["name"] == "show_user_options":
                            logger.info(f"chat_container tool_call.function.arguments: {tool_call['function']['arguments']}")
                            
                            args = tool_call["function"]["arguments"]
                            st.markdown(f"**{args['prompt']}**")
                            
                            num_choices = len(args['choices'])

                            logger.info(f"chat_container num_choices: {num_choices}")
                            
                            if num_choices > 0:
                                cols = st.columns(max(1, num_choices))
                                for i, choice in enumerate(args['choices']):
                                    with cols[i]:
                                        if st.button(str(choice), use_container_width=True):
                                            st.session_state.messages.append({
                                                "role": "user",
                                                "content": str(choice)
                                            })
                                            st.session_state.processing = True
                                            # st.rerun()

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

