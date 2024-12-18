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

    # Add class variable to track current instance
    _current_instance = None

    # Default LLM settings
    AGENT_TEMPERATURE = 0.5  # For main assistant responses
    CREATIVE_TEMPERATURE = 0.8  # For creative writing tool

    # Add seed to class-level defaults
    AGENT_SEED = None  # Default to random seed
    CREATIVE_SEED = None  # Default to random seed

    def __init__(
        self,
        storage_path: str = "assistant_state.json",
        system_prompt: Optional[str] = "",
        agent_temperature: Optional[float] = None,
        creative_temperature: Optional[float] = None,
        agent_seed: Optional[int] = None,  # Add seed parameters
        creative_seed: Optional[int] = None,
    ):
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
            'set_property': self.set_property,
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

    def _call_llm(self):
        """Calls the LLM via Ollama."""
        ollama_client = ollama.Client(transport=LoggingTransport())

        # Create a temporary list of messages for this LLM call
        # Get all prepended messages (system prompts etc)
        messages_for_llm = [msg.model_dump() for msg in self.get_prepended_messages()]
        # Add the actual chat history
        messages_for_llm.extend([msg.model_dump() for msg in self.chat_session.messages])

        # Adjust num_predict or other parameters as needed
        num_predict = 2000

        options = {
            'num_ctx': 10000,
            'num_predict': num_predict,
            "temperature": self.agent_temperature,  # Use agent temperature
            "mirostat": 1,
            'seed': self.agent_seed if self.agent_seed is not None else random.randint(0, 1000000),
        }

        kwargs = {
            'model': self.MODEL,
            'messages': messages_for_llm,  # Use the temporary message list
            'options': options,
            'keep_alive': "1h",
        }
        
        # Only include tools if the last message allows tool calls
        last_message = self.chat_session.messages[-1] if self.chat_session.messages else None
        if self.available_tools and (not last_message or last_message.allow_tool_calls):
            kwargs['tools'] = list(self.available_tools.values())

        response = ollama_client.chat(**kwargs)

        # Handle dict response from Ollama
        if response['message']['content']:
            # Only add the response to the actual chat history
            self.chat_session.messages.append(Message(
                role="assistant",
                content=response['message']['content'],
                timestamp=datetime.now().isoformat(),
                show_user=True  # Always show assistant messages
            ))

        # Check for tool calls in dict response
        if response['message'].get('tool_calls'):
            # # Add assistant message if it wasn't added above
            # if not response['message'].get('content'):
            #     self.chat_session.messages.append(Message(
            #         role="assistant", 
            #         content=response['message']['content'],
            #         timestamp=datetime.now().isoformat(),
            #         show_user=True
            #     ))
            
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
                self.chat_session.messages.append(Message(
                    role="tool",
                    content=result,
                    timestamp=datetime.now().isoformat(),
                    show_user=metadata.show_output,
                    ephemeral=False
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
        """
        After we have tool outputs in messages, we call LLM again to integrate those results.
        Then we see if the LLM wants more tools or just final output.
        """
        ollama_client = ollama.Client(transport=LoggingTransport())

        # For a shared system prompt, prepend it to the messages:
        system_message = Message(role=ROLE_SYSTEM, content=self.system_prompt)
        extra_messages = [Message(
            role="system",
            content=f"Check the following output and set any properties that are needed to make the story match the result, asking the user first unless they already gave permission.",
            timestamp=datetime.now().isoformat(),
            show_user=False
        ).model_dump()]
        full_messages = [system_message.model_dump()] + extra_messages +[msg.model_dump() for msg in self.chat_session.messages]

        num_predict = 2000
        options = {
            'num_ctx': 10000,
            'num_predict': num_predict,
            "temperature": self.agent_temperature,  # Use agent temperature
            "mirostat": 1,
            'seed': self.agent_seed if self.agent_seed is not None else random.randint(0, 1000000),
        }

        response = ollama_client.chat(
            self.MODEL,
            messages=full_messages,
            tools=list(self.available_tools.values()),
            options=options,
            keep_alive="1h",
        )

        if response['message'].get('tool_calls'):
            self.tool_calls = [
                ToolCall(
                    name=tc['function']['name'],
                    arguments=tc['function']['arguments']  # Just pass the dict directly
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
    def tool(emoji: str = "🔧", description: str = "", show_output: bool = True):
        """Decorator to mark assistant methods as tools and store their metadata.
        
        Args:
            emoji (str): Emoji icon for the tool
            description (str): Tool description for documentation
            show_output (bool): Whether to show the tool output in chat
        """
        def decorator(func):
            # Store metadata on the function object
            metadata = ToolMetadata(
                name=func.__name__,
                emoji=emoji,
                description=description or func.__doc__,
                show_output=show_output
            )
            func._tool_metadata = metadata
            return func
        return decorator

    @tool(emoji="✏️", description="Sets a property value in the story")
    def set_property(self, property_name: str, value: str) -> str:
        """Sets the specified property of the story to the given value. If the user gives you any useful information, set the property to that value. If a tool gives you any useful information, ask the user if they like it and if they do, set the property to that value.
        
        Args:
            property_name (str): The name of the property to set (must be a valid story attribute)
            value (str): The value to set the property to
            
        Returns:
            str: A message describing what was updated
        """
        if not hasattr(self, 'story'):
            return "Error: No story object available"
        
        story = self.story
        if hasattr(story, property_name):
            # Get current value for comparison
            old_value = getattr(story, property_name)
            
            # Only save state if we're actually changing the value
            if old_value != value:
                try:
                    # Set the new value
                    setattr(story, property_name, value)
                    
                    # Re-validate the story model
                    story = Story(**story.model_dump())
                    self.story = story
                    
                    # Set success status for UI
                    self.set_status('success', f'Successfully updated property `{property_name}`')
                    
                    if old_value:
                        return f"**Updated `{property_name}`** from `{repr(old_value)}` to: `{repr(value)}`\n\n---\n\n"
                    else:
                        return f"**Set `{property_name}`** to: `{repr(value)}`\n\n---\n\n"
                except Exception as e:
                    self.set_status('error', f'Failed to update {property_name}: {str(e)}')
                    return f"Error setting property {property_name} to {value}. \n\n{e}"
            else:
                self.set_status('info', f'Property {property_name} already has this value')
                return f"Property {property_name} already has value: `{value}`"
        else:
            self.set_status('error', f'Property {property_name} does not exist')
            return f"Property '{property_name}' does not exist in the story."

    @tool(emoji="✍️", description="Generates creative content", show_output=False)
    def creative_write(self, prompt: str, system_context: str = "", story_context: str = "") -> str:
        """A creative writer will write about the prompt you provide. No context is passed to the writer, so be sure to include all relevant information. For example if you have a genre, you should ask to write about something in that specific genre. Take into account any requests the user has made.

        Args:
            prompt (str): Tells the writer what to write about.
            system_context (str, optional): Additional system-level context/instructions. Defaults to "".
            story_context (str, optional): Story-specific context. Defaults to "". The writer will be unaware of any context that is not passed into these two arguments, so be sure to include all relevant information.

        Returns:
            str: The generated creative content.
        """
        ollama_client = ollama.Client(transport=LoggingTransport())
        
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
        
        options = {
            'num_ctx': 10000,
            'num_predict': 5000,
            "temperature": self.creative_temperature,  # Use creative temperature
            "mirostat": 1,
            'seed': self.creative_seed if self.creative_seed is not None else random.randint(0, 1000000),
        }
        
        # Stream the response
        stream = ollama_client.chat(
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
