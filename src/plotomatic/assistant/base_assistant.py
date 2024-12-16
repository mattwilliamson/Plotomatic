# assistant/base_assistant.py

import json
import random
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime

import ollama
from .ollama_logging import LoggingTransport

from .states import AssistantState
from ..models import Story
from ..models.chat import Message, ChatSession, ToolCall

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
        "You are a helpful assistant that uses function calls (tools) when necessary. "
        "Maintain context for the conversation and respond clearly."
    )

    MODEL = "llama3.3"  # Replace DEFAULT_OLLAMA_MODEL with this

    # Class-level constants for states. Alternatively, import from states.py:
    STATE_GENERATING_OUTPUT = AssistantState.GENERATING_OUTPUT
    STATE_WAITING_USER_INPUT = AssistantState.WAITING_USER_INPUT
    STATE_PROCESSING_TOOL_CALLS = AssistantState.PROCESSING_TOOL_CALLS
    STATE_PROCESSING_TOOL_OUTPUTS = AssistantState.PROCESSING_TOOL_OUTPUTS

    # Add class variable to track current instance
    _current_instance = None

    def __init__(
        self,
        storage_path: str = "assistant_state.json",
        system_prompt: Optional[str] = None,
    ):
        self.storage_path = storage_path

        # If no system prompt is specified, fall back to base
        self.system_prompt = system_prompt or self.BASE_SYSTEM_PROMPT

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

    def send_message(self, user_message: str):
        """User sends a message to the assistant. This sets the state to generating output and reloads."""
        self.chat_session.messages.append(Message(
            role="user",
            content=user_message,
            timestamp=datetime.now().isoformat()
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

    def _call_llm(self):
        """Calls the LLM via Ollama."""
        ollama_client = ollama.Client(transport=LoggingTransport())

        # For a shared system prompt, prepend it to the messages:
        system_message = Message(role="system", content=self.system_prompt)
        full_messages = [system_message.model_dump()] + [msg.model_dump() for msg in self.chat_session.messages]

        # Adjust num_predict or other parameters as needed
        num_predict = 512

        options = {
            'num_ctx': 6000,
            'num_predict': num_predict,
            "temperature": 0.5,
            "mirostat": 1,
            'seed': random.randint(0, 1000000),
        }

        response = ollama_client.chat(
            self.MODEL,
            messages=full_messages,
            tools=list(self.available_tools.values()),
            options=options,
            keep_alive="1h",
        )

        # Handle dict response from Ollama
        if response['message']['content']:
            self.chat_session.messages.append(Message(
                role="assistant",
                content=response['message']['content'],
                timestamp=datetime.now().isoformat()
            ))

        # Check for tool calls in dict response
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
            self.state = self.STATE_WAITING_USER_INPUT

    def _execute_tool_calls(self):
        """
        Execute the first tool call in the queue.
        Add the tool result to messages as a 'tool' role message.
        If more calls remain, stay in PROCESSING_TOOL_CALLS. Otherwise, go to PROCESSING_TOOL_OUTPUTS.
        """
        if not self.tool_calls:
            # No calls to process, move on
            self.state = self.STATE_PROCESSING_TOOL_OUTPUTS
            return

        current_call = self.tool_calls.pop(0)  # Take the first call
        # Use the new structure directly
        function_name = current_call.name
        arguments = current_call.arguments

        function_to_call = self.available_tools.get(function_name)
        if function_to_call:
            tool_result = function_to_call(**arguments)
            # Add the tool result to the conversation
            self.chat_session.messages.append(Message(
                role="tool",
                content=str(tool_result),
                timestamp=datetime.now().isoformat()
            ))
        else:
            # Tool function not found
            self.chat_session.messages.append(Message(
                role="tool",
                content=f"Tool not found: {function_name}",
                timestamp=datetime.now().isoformat()
            ))

        # If more tool calls remain, we stay in PROCESSING_TOOL_CALLS
        if self.tool_calls:
            self.state = self.STATE_PROCESSING_TOOL_CALLS
        else:
            # Once all tools are processed, re-check LLM with the new tool messages
            self.state = self.STATE_PROCESSING_TOOL_OUTPUTS

    def _process_tool_outputs(self):
        """
        After we have tool outputs in messages, we call LLM again to integrate those results.
        Then we see if the LLM wants more tools or just final output.
        """
        ollama_client = ollama.Client(transport=LoggingTransport())

        # For a shared system prompt, prepend it to the messages:
        system_message = Message(role="system", content=self.system_prompt)
        full_messages = [system_message.model_dump()] + [msg.model_dump() for msg in self.chat_session.messages]

        num_predict = 512
        options = {
            'num_ctx': 6000,
            'num_predict': num_predict,
            "temperature": 0.5,
            "mirostat": 1,
            'seed': random.randint(0, 1000000),
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

    def register_tool(self, func):
        """
        Register a Python function as a tool for the LLM to call.
        Typically you'd do: assistant.register_tool(set_property).
        """
        self.available_tools[func.__name__] = func

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
