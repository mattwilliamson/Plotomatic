# assistant/base_assistant.py

import json
import random
import os
from typing import List, Dict, Optional, Tuple, Callable, Any, Union
from datetime import datetime
from functools import wraps

import ollama
from .ollama_logging import LoggingTransport

from .states import AssistantState
from plotomatic.models import Story
from plotomatic.models.chat import Message, ChatSession, ToolCall, ROLE_SYSTEM, ROLE_USER, ROLE_ASSISTANT, ROLE_TOOL
from .tool_metadata import ToolMetadata

class BaseChatAssistant:
    """
    Base class for a chat assistant that manages:
      - State machine transitions
      - LLM calls using Ollama
      - Tool calls
      - Quick-response options
      - Message history persistence
    """

    BASE_SYSTEM_PROMPT = (
        "You are Plotomatic. A helpful assistant that helps a user write a story. "
        # "Be proactive and offer to be creative and help the user fill out the story. "
    )

    MODEL = "llama3.3"  # Replace DEFAULT_OLLAMA_MODEL with this

    # Class-level constants for states. Alternatively, import from states.py:
    STATE_GENERATING_OUTPUT = AssistantState.GENERATING_OUTPUT
    STATE_WAITING_USER_INPUT = AssistantState.WAITING_USER_INPUT
    STATE_PROCESSING_TOOL_CALLS = AssistantState.PROCESSING_TOOL_CALLS
    STATE_PROCESSING_TOOL_OUTPUTS = AssistantState.PROCESSING_TOOL_OUTPUTS
    STATE_QUESTIONING_TOOL_OUTPUT = AssistantState.QUESTIONING_TOOL_OUTPUT

    # Add class variable to track current instance
    _current_instance = None

    # Default LLM settings
    AGENT_TEMPERATURE = 0.5  # For main assistant responses
    CREATIVE_TEMPERATURE = 0.8  # For creative writing tool

    # Add seed to class-level defaults
    AGENT_SEED = None  # Default to random seed
    CREATIVE_SEED = None  # Default to random seed

    # Default LLM options
    DEFAULT_OPTIONS = {
        'num_ctx': 10000,
        'num_predict': 2000,
        'temperature': 0.5,  # Default agent temperature
        # 'mirostat': 1,
    }

    # Class-level client
    _ollama_client: Optional[ollama.Client] = None

    def __init__(
        self,
        storage_path: str = "assistant_state.json",
        system_prompt: Optional[str] = "",
        agent_temperature: Optional[float] = None,
        creative_temperature: Optional[float] = None,
        agent_seed: Optional[int] = None,  # Add seed parameters
        creative_seed: Optional[int] = None,
    ):
        # Initialize shared client if not exists
        if BaseChatAssistant._ollama_client is None:
            BaseChatAssistant._ollama_client = ollama.Client(transport=LoggingTransport())

        self.storage_path = storage_path

        self.system_prompt = system_prompt

        # Replace messages list with ChatSession
        self.chat_session = ChatSession(project="", messages=[])

        # A queue of tool calls that the LLM requests
        self.tool_calls: List[ToolCall] = []

        # Quick response options (UI can display these as buttons)
        self.quick_responses: List[str] = []

        # Current state
        self.state = self.STATE_GENERATING_OUTPUT

        # Tools (function references) available to this assistant
        self.available_tools = {}

        # Attempt load from file to restore state
        self.load_state()

        self.story: Optional[Story] = None
        self._status: Optional[Tuple[str, str]] = None  # (type, message)
        BaseChatAssistant._current_instance = self

        self.prepended_messages: List[Message] = []
        self.initialize_prepended_messages()

        # Define the default available tools as instance methods
        self._default_tools = {
            'set_properties': self.set_properties,
            'creative_write': self.creative_write
        }
        
        # Initialize available tools with defaults
        self.available_tools = self._default_tools.copy()

        # Add state for tracking current tool execution
        self.current_tool_status: Optional[str] = None

        # Set temperatures, allowing override from constructor
        self.agent_temperature = agent_temperature if agent_temperature is not None else self.AGENT_TEMPERATURE
        self.creative_temperature = creative_temperature if creative_temperature is not None else self.CREATIVE_TEMPERATURE

        # Set seeds, allowing override from constructor
        self.agent_seed = agent_seed if agent_seed is not None else self.AGENT_SEED
        self.creative_seed = creative_seed if creative_seed is not None else self.CREATIVE_SEED

    @classmethod
    def get_current(cls) -> 'BaseChatAssistant':
        """Get the current assistant instance."""
        if not cls._current_instance:
            raise RuntimeError("No assistant instance available")
        return cls._current_instance

    def save_state(self):
        """
        Save relevant data to disk so the assistant can be reloaded.
        """
        data = {
            "chat_session": self.chat_session.model_dump(),
            "tool_calls": [tc.model_dump() for tc in self.tool_calls],
            "quick_responses": self.quick_responses,
            "state": self.state,
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_state(self):
        """
        Load previously saved state from disk, if available.
        """
        if not os.path.exists(self.storage_path):
            return  # No state file, just skip

        with open(self.storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.chat_session = ChatSession(**data.get("chat_session", {"project": "", "messages": []}))
            self.tool_calls = [ToolCall(**tc) for tc in data.get("tool_calls", [])]
            self.quick_responses = data.get("quick_responses", [])
            self.state = data.get("state", self.STATE_GENERATING_OUTPUT)

    def clear_quick_responses(self):
        self.quick_responses = []

    def set_quick_responses(self, responses: List[str]):
        """Set dynamic quick response options (e.g., 'Confirm', 'Cancel')."""
        self.quick_responses = responses

    def send_message(self, message: str):
        """Send a user message to the assistant."""
        self.chat_session.messages.append(Message(
            role="user",
            content=message,
            timestamp=datetime.now().isoformat(),
            show_user=True  # Always show user messages
        ))
        self.state = self.STATE_GENERATING_OUTPUT
        self.save_state()

    def run(self):
        """
        The main method to be called by the UI (e.g., Streamlit) each time the page loads.
        It checks the current state and acts accordingly.
        """
        if self.state == self.STATE_GENERATING_OUTPUT:
            self.clear_quick_responses()
            # Call the LLM with the current messages to get a response (or tool calls)
            self._call_llm()
            self.save_state()

        elif self.state == self.STATE_PROCESSING_TOOL_CALLS:
            self.clear_quick_responses()
            self._execute_tool_calls()
            self.save_state()

        elif self.state == self.STATE_PROCESSING_TOOL_OUTPUTS:
            self.clear_quick_responses()
            self._process_tool_outputs()
            self.save_state()

        elif self.state == self.STATE_QUESTIONING_TOOL_OUTPUT:
            self.clear_quick_responses()
            self._question_tool_output()
            self.save_state()

        elif self.state == self.STATE_WAITING_USER_INPUT:
            # No-op: just waiting for user input
            pass

        self._status = None

    def initialize_prepended_messages(self):
        """Initialize the list of messages that will be prepended to every LLM call.
        Override this in subclasses to add more context-specific messages."""
        self.prepended_messages = [
            Message(
                role=ROLE_SYSTEM,
                content=self.system_prompt,
                allow_tool_calls=True
            )
        ]

    def get_prepended_messages(self) -> List[Message]:
        """Get the list of messages to prepend before each LLM call.
        Override this in subclasses to add dynamic content."""
        return self.prepended_messages

    def _get_llm_options(self, temperature: Optional[float] = None, seed: Optional[int] = None) -> dict:
        """Get LLM options with optional overrides."""
        options = self.DEFAULT_OPTIONS.copy()
        if temperature is not None:
            options['temperature'] = temperature
        if seed is not None:
            options['seed'] = seed
        return options

    def _call_llm(self):
        """Calls the LLM via Ollama."""
        # Create a temporary list of messages for this LLM call
        messages_for_llm = [msg.model_dump() for msg in self.get_prepended_messages()]
        messages_for_llm.extend([msg.model_dump() for msg in self.chat_session.messages])

        # Get options with agent temperature and seed
        options = self._get_llm_options(
            temperature=self.agent_temperature,
            seed=self.agent_seed if self.agent_seed is not None else random.randint(0, 1000000)
        )

        kwargs = {
            'model': self.MODEL,
            'messages': messages_for_llm,
            'options': options,
            'keep_alive': "1h",
        }
        
        # Only include tools if the last message allows tool calls
        last_message = self.chat_session.messages[-1] if self.chat_session.messages else None
        if self.available_tools and (not last_message or last_message.allow_tool_calls):
            kwargs['tools'] = list(self.available_tools.values())

        response = self._ollama_client.chat(**kwargs)

        # Handle dict response from Ollama
        if response['message']['content'] or response['message'].get('tool_calls'):
            # Format tool calls if present
            tool_calls = None
            if response['message'].get('tool_calls'):
                tool_calls = [
                    {
                        "function": {
                            "name": tc['function']['name'],
                            "arguments": tc['function']['arguments']
                        }
                    }
                    for tc in response['message']['tool_calls']
                ]

            # Add the assistant's message to chat history with any tool calls
            self.chat_session.messages.append(Message(
                role="assistant",
                content=response['message'].get('content', ''),
                timestamp=datetime.now().isoformat(),
                show_user=True,  # Always show assistant messages
                tool_calls=tool_calls  # Include tool calls in the message
            ))

            # Set tool calls and state for processing
            if tool_calls:
                self.tool_calls = [
                    ToolCall(
                        name=tc['function']['name'],
                        arguments=tc['function']['arguments']
                    )
                    for tc in response['message']['tool_calls']
                ]
                self.state = self.STATE_PROCESSING_TOOL_CALLS
            else:
                self.state = self.STATE_WAITING_USER_INPUT

    def _execute_tool_calls(self):
        """Execute the first tool call in the queue."""
        if not self.tool_calls:
            self.state = self.STATE_PROCESSING_TOOL_OUTPUTS
            return

        current_call = self.tool_calls.pop(0)
        function_name = current_call.name
        arguments = current_call.arguments

        self.current_tool = current_call
        self.current_tool_status = f"Executing {function_name}..."

        try:
            function_to_call = self.available_tools.get(function_name)
            if function_to_call:
                tool_result = function_to_call(**arguments)
                
                # Handle generator results from creative_write
                if hasattr(tool_result, '__iter__') and not isinstance(tool_result, str):
                    # For generators, we'll store the generator in a special attribute
                    self._current_stream = tool_result
                    # Return a placeholder - the actual content will be streamed
                    tool_result = "<streaming content>"
                
                metadata = self.get_tool_metadata(function_name)
                result = f"Tool output for {function_name}:\n{tool_result}"
                # self.chat_session.messages.append(Message(
                #     role="system",
                #     content="Ask the user if they like this if they haven't already given permission, and if they do consent, set the properties to those values. For long strings, like plot_overview, use the full text. Don't abridge it.",
                #     timestamp=datetime.now().isoformat(),
                #     show_user=metadata.show_output,
                #     ephemeral=False
                # ))
                self.chat_session.messages.append(Message(
                    role="tool",
                    content=result,
                    timestamp=datetime.now().isoformat(),
                    show_user=metadata.show_output,
                    ephemeral=False,
                    tool_name=function_name  # Add tool name to message
                ))
            else:
                self.chat_session.messages.append(Message(
                    role="tool",
                    content=f"Tool not found: {function_name}",
                    timestamp=datetime.now().isoformat(),
                    show_user=True
                ))
        finally:
            self.current_tool = None
            self.current_tool_status = None

        if self.tool_calls:
            self.state = self.STATE_PROCESSING_TOOL_CALLS
        else:
            self.state = self.STATE_PROCESSING_TOOL_OUTPUTS

    def _process_tool_outputs(self):
        """Process tool outputs using shared client."""
        # Get the last tool message's metadata
        last_tool_message = next((msg for msg in reversed(self.chat_session.messages) 
                                if msg.role == ROLE_TOOL), None)
        if last_tool_message and hasattr(last_tool_message, 'tool_name'):
            tool_metadata = self.get_tool_metadata(last_tool_message.tool_name)
            if tool_metadata.needs_questioning:
                self.state = self.STATE_QUESTIONING_TOOL_OUTPUT
                return

        # Get prepended messages and extend with chat session messages
        full_messages = [msg.model_dump() for msg in self.get_prepended_messages()]
        full_messages.extend([msg.model_dump() for msg in self.chat_session.messages])

        # Get options with agent temperature and seed
        options = self._get_llm_options(
            temperature=self.agent_temperature,
            seed=self.agent_seed if self.agent_seed is not None else random.randint(0, 1000000)
        )

        response = self._ollama_client.chat(
            model=self.MODEL,
            messages=full_messages,  # Use the combined messages
            tools=list(self.available_tools.values()),
            options=options,
            keep_alive="1h",
        )

        if response['message'].get('tool_calls'):
            tool_calls = [
                {
                    "function": {
                        "name": tc['function']['name'],
                        "arguments": tc['function']['arguments']
                    }
                }
                for tc in response['message']['tool_calls']
            ]
            
            # Add the assistant's message to chat history with tool calls
            self.chat_session.messages.append(Message(
                role="assistant",
                content=response['message'].get('content', ''),
                timestamp=datetime.now().isoformat(),
                show_user=True,
                tool_calls=tool_calls
            ))

            # Set tool calls for processing
            self.tool_calls = [
                ToolCall(
                    name=tc['function']['name'],
                    arguments=tc['function']['arguments']
                )
                for tc in response['message']['tool_calls']
            ]
            self.state = self.STATE_PROCESSING_TOOL_CALLS
        else:
            if response['message']['content']:
                self.chat_session.messages.append(Message(
                    role="assistant",
                    content=response['message']['content'],
                    timestamp=datetime.now().isoformat()
                ))
            self.state = self.STATE_WAITING_USER_INPUT

    def _question_tool_output(self):
        """
        Ask questions about the tool output before presenting to user.
        """
        ollama_client = ollama.Client(transport=LoggingTransport())

        # Add a system message specifically for questioning the output
        questioning_prompt = """Review the previous tool output and ask relevant questions to ensure it meets the user's needs. If there is any useful information in the output, ask the user if they like it. If they do, set any properties that are needed to make the story match the result."""

        messages = [
            Message(role=ROLE_SYSTEM, content=questioning_prompt).model_dump(),
            *[msg.model_dump() for msg in self.chat_session.messages]
        ]

        options = {
            'num_ctx': 10000,
            'num_predict': 2000,
            "temperature": self.agent_temperature,
            # "mirostat": 1,
            'seed': self.agent_seed if self.agent_seed is not None else random.randint(0, 1000000),
        }

        response = ollama_client.chat(
            self.MODEL,
            messages=messages,
            options=options,
            keep_alive="1h",
        )

        if response['message']['content']:
            self.chat_session.messages.append(Message(
                role="assistant",
                content=response['message']['content'],
                timestamp=datetime.now().isoformat()
            ))
        self.state = self.STATE_WAITING_USER_INPUT

    def register_tools(self, tools: Dict[str, Callable]):
        """Register multiple tools at once.
        
        Args:
            tools (Dict[str, Callable]): Dictionary of tool name to function mappings
        """
        self.available_tools.update(tools)

    def register_tool(self, name_or_func: Union[str, Callable], func: Optional[Callable] = None):
        """Register a single tool or enable a built-in tool.
        
        Args:
            name_or_func (Union[str, Callable]): Name of built-in tool or function to register
            func (Optional[Callable]): Function to register if first arg is name
        """
        if isinstance(name_or_func, str):
            # Register by name
            if func is not None:
                # Register custom tool with given name
                self.available_tools[name_or_func] = func
            else:
                # Enable built-in tool
                if name_or_func in self._default_tools:
                    self.available_tools[name_or_func] = self._default_tools[name_or_func]
                else:
                    raise ValueError(f"No built-in tool named {name_or_func}")
        else:
            # Register function directly
            func = name_or_func
            self.available_tools[func.__name__] = func

    def get_tool_metadata(self, tool_name: str) -> ToolMetadata:
        """Get metadata for a tool including its emoji.
        
        Args:
            tool_name (str): Name of the tool
            
        Returns:
            ToolMetadata: Tool metadata including emoji, description, and show_output
        """
        tool_func = self.available_tools.get(tool_name)
        if tool_func and hasattr(tool_func, '_tool_metadata'):
            return tool_func._tool_metadata
        return ToolMetadata(name=tool_name)

    def get_tool_emoji(self, tool_name: str) -> str:
        """Get the emoji for a tool.
        
        Args:
            tool_name (str): Name of the tool
            
        Returns:
            str: The tool's emoji or default emoji
        """
        metadata = self.get_tool_metadata(tool_name)
        return metadata.emoji

    def set_status(self, status_type: str, message: str):
        """Set a status message to be displayed by the UI.
        
        Args:
            status_type (str): One of 'success', 'error', 'info'
            message (str): The status message
        """
        self._status = (status_type, message)

    def get_and_clear_status(self) -> Optional[Tuple[str, str]]:
        """Get and clear the current status.
        
        Returns:
            Optional[Tuple[str, str]]: The current status tuple (type, message) or None
        """
        status = self._status
        self._status = None
        return status

    def add_ephemeral_message(self, role: str, content: str, allow_tool_calls: bool = True):
        """
        Add a message that will be sent to the LLM but not saved in chat history.
        Useful for injecting context or instructions that shouldn't persist.
        
        Args:
            role (str): The role of the message sender ("system", "user", or "assistant")
            content (str): The message content
            allow_tool_calls (bool): Whether to allow tool calls for this message
        """
        self.chat_session.messages.append(Message(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            show_user=False,
            ephemeral=True,  # Flag to mark message as temporary
            allow_tool_calls=allow_tool_calls
        ))

    @staticmethod
    def tool(emoji: str = "🔧", description: str = "", show_output: bool = True, needs_questioning: bool = False):
        """Decorator to mark assistant methods as tools and store their metadata.
        
        Args:
            emoji (str): Emoji icon for the tool
            description (str): Tool description for documentation
            show_output (bool): Whether to show the tool output in chat
            needs_questioning (bool): Whether the tool output should be questioned before presenting to user
        """
        def decorator(func):
            # Store metadata on the function object
            metadata = ToolMetadata(
                name=func.__name__,
                emoji=emoji,
                description=description or func.__doc__,
                show_output=show_output,
                needs_questioning=needs_questioning
            )
            func._tool_metadata = metadata
            return func
        return decorator

    @tool(emoji="✏️", description="Sets multiple property values in the story")
    def set_properties(self, properties: dict) -> str:
        """Sets multiple properties of the story to the given values. If the user gives you any useful information, set the properties to those values. If a tool gives you any useful information, ask the user if they like it and if they do, set the properties to those values. For long strings, like plot_overview, use the full text.
        
        Args:
            properties (dict): Dictionary mapping property names to their values
            
        Returns:
            str: A message describing what was updated
        """
        if not hasattr(self, 'story'):
            return "Error: No story object available"
        
        story = self.story
        updates = []
        errors = []
        
        for property_name, value in properties.items():
            if hasattr(story, property_name):
                # Get current value for comparison
                old_value = getattr(story, property_name)
                
                # If the property is a list type and value isn't already a list,
                # try to JSON decode the value
                if isinstance(old_value, list) and not isinstance(value, list):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        # If JSON decoding fails, treat it as a single-item list
                        value = [value]
                
                # Only save state if we're actually changing the value
                if old_value != value:
                    try:
                        # Set the new value
                        setattr(story, property_name, value)
                        
                        # Track successful update
                        if old_value:
                            updates.append(f"Updated `{property_name}`")
                        else:
                            updates.append(f"Set `{property_name}`")
                            
                    except Exception as e:
                        errors.append(f"Failed to update {property_name}: {str(e)}")
                else:
                    updates.append(f"Property {property_name} already has that value")
            else:
                errors.append(f"Property '{property_name}' does not exist")

        try:
            # Re-validate the story model after all updates
            story = Story(**story.model_dump())
            self.story = story
            
            if updates:
                self.set_status('success', 'Successfully updated properties')
            
            # Call LLM to analyze for other potential properties
            ollama_client = ollama.Client(transport=LoggingTransport())
            
            analysis_prompt = f"""You are an expert story critic. You are given a story and properties that were just set as the user updates the story. Based on the current story state, what other properties could we extrapolate and update to match the overall story? For example:

- If plot_overview was set, look for locations, time periods, or themes
- If genre was set, look for subgenres or themes
- If title was set, look for themes or genre hints
- Don't make up new properties, only use the ones that are already established in the story.
- If plot_overview is blank, don't make up one, another assistant will do that.

Current story context:
{self._format_story_state()}

Analyze the story and provide a list of properties by exact field name and their corresponding values that need to be updated to match the overall story.

- Only respond with a list of properties and their suggested values, don't include thoughts or explanations.
- Don't make up new properties, only use the ones that are already established in the story.
- Don't make up an author name, unless explicitly asked.
- If all the properties look good, just say "No suggestions"

"""
            analysis_user_prompt = f"""The user just updated these properties: {', '.join(property_name for property_name in properties.keys())}"""

            analysis_response = ollama_client.chat(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": analysis_prompt},
                    {"role": "user", "content": analysis_user_prompt}
                ],
                options = {
                    'num_ctx': 10000,
                    'num_predict': 5000,
                    "temperature": self.agent_temperature,
                    # "mirostat": 1,
                    'seed': self.agent_seed if self.agent_seed is not None else random.randint(0, 1000000),
                }
            )

            suggestions = analysis_response['message']['content']
            
            # Only include suggestions section if there are actual suggestions
            suggestions_text = f"\n\nSuggestions to present to the user:\n\n{suggestions}" if suggestions and "No suggestions" not in suggestions else ""
            
            return f"**Updates:**\n" + "\n".join(updates) + (f"\n\n**Errors:**\n" + "\n".join(errors) if errors else "") + suggestions_text

        except Exception as e:
            self.set_status('error', f'Failed to update properties: {str(e)}')
            return f"Error updating properties: {str(e)}"

    # @tool(emoji="✍️", description="Generates creative content", show_output=False, needs_questioning=True)
    @tool(emoji="✍️", description="Generates creative content", show_output=False, needs_questioning=False)
    def creative_write(self, prompt: str, system_context: str = "", story_context: str = "") -> str:
        """Creative writing tool using shared client."""
        messages = []
        
        # Add default Plotomatic system context
        plotomatic_context = f"""You are a creative writing assistant for Plotomatic, a story development tool. 
Your goal is to help writers develop their stories by generating creative, engaging, and coherent content.
Write in a clear, descriptive style that brings scenes and characters to life.
Focus on showing rather than telling, and maintain consistency with the provided story context.

Current Story Context:
{self.story.model_dump_json(indent=2)}
"""
        
        # Combine default context with user-provided context
        full_system_context = plotomatic_context
        if system_context:
            full_system_context += "\n" + system_context
        
        messages.append({"role": "system", "content": full_system_context})
        messages.append({"role": "user", "content": "Based on the story context: " + prompt})
        
        # Get options with creative temperature and seed
        options = self._get_llm_options(
            temperature=self.creative_temperature,
            seed=self.creative_seed if self.creative_seed is not None else random.randint(0, 1000000)
        )
        
        # Stream the response
        stream = self._ollama_client.chat(
            model=self.MODEL,
            messages=messages,
            options=options,
            stream=True,
        )
        
        # Create a generator that accumulates the response while yielding chunks
        def accumulating_stream():
            full_response = ""
            for chunk in stream:
                if chunk['message']['content']:
                    content = chunk['message']['content']
                    full_response += content
                    yield content
            # Store the full response
            self._last_creative_response = full_response
            
        # Store the generator for UI streaming
        self._current_stream = accumulating_stream()
        
        # For the assistant, consume the stream to get the full response
        full_response = ""
        for chunk in self._current_stream:
            full_response += chunk
            
        return full_response

    def get_current_tool(self) -> Optional[ToolCall]:
        """Get the currently executing tool call."""
        return getattr(self, 'current_tool', None)

    def get_current_tool_status(self) -> Optional[str]:
        """Get the current tool execution status message."""
        return self.current_tool_status

    def get_current_stream(self):
        """Get the current streaming content generator if any."""
        return getattr(self, '_current_stream', None)
