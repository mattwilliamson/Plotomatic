# tests/test_base_assistant.py

import json
import pytest
from unittest.mock import patch, MagicMock

from plotomatic.assistant.base_assistant import BaseChatAssistant
from plotomatic.assistant.states import AssistantState
from plotomatic.models.chat import Message, ChatSession, ToolCall

@pytest.fixture
def mock_ollama_chat():
    """
    A pytest fixture to mock the ollama.Client.chat call.
    We can configure different responses (tool calls, no tool calls, etc.) via yield.
    """
    with patch("ollama.Client.chat", autospec=True) as mock_chat:
        yield mock_chat

@pytest.fixture
def temp_storage_path(tmp_path):
    """
    A pytest fixture providing a temporary file path to store the assistant state.
    Ensures we don't pollute real file system with test data.
    """
    return str(tmp_path / "test_base_assistant_state.json")

@pytest.fixture
def base_assistant(temp_storage_path):
    """
    Creates a fresh instance of BaseChatAssistant with a temporary storage path.
    """
    assistant = BaseChatAssistant(storage_path=temp_storage_path)
    return assistant

def test_base_assistant_initial_state(base_assistant):
    """
    Test that the BaseChatAssistant initializes with correct default values.
    """
    assert base_assistant.state == base_assistant.STATE_GENERATING_OUTPUT
    assert len(base_assistant.chat_session.messages) == 0  # Empty messages list
    assert base_assistant.tool_calls == []
    assert base_assistant.quick_responses == []
    assert base_assistant.system_prompt in base_assistant.BASE_SYSTEM_PROMPT
    assert base_assistant.available_tools == {}

def test_run_no_tool_calls(base_assistant, mock_ollama_chat):
    """
    Test the run method when the LLM does not request any tool calls.
    """
    # Simulate Ollama's dict response structure
    mock_resp = {
        'message': {
            'content': 'Hello from the base LLM.',
            'tool_calls': None
        }
    }
    mock_ollama_chat.return_value = mock_resp

    base_assistant.run()

    # We expect one assistant message appended
    assert len(base_assistant.chat_session.messages) == 1
    assert base_assistant.chat_session.messages[0].role == "assistant"
    assert base_assistant.chat_session.messages[0].content == "Hello from the base LLM."
    assert base_assistant.state == base_assistant.STATE_WAITING_USER_INPUT

def test_send_message_transitions(base_assistant, mock_ollama_chat):
    """
    Test sending a user message, verifying state transitions and final LLM output.
    """
    # 1) Initial run to produce a greeting or initial output
    mock_resp = {
        'message': {
            'content': 'Initial greeting from LLM.',
            'tool_calls': None
        }
    }
    mock_ollama_chat.return_value = mock_resp

    base_assistant.run()
    assert base_assistant.state == AssistantState.WAITING_USER_INPUT

    # 2) Simulate user sending a message
    base_assistant.send_message("User's question about the story.")
    assert base_assistant.chat_session.messages[-1].role == "user"
    assert base_assistant.chat_session.messages[-1].content == "User's question about the story."
    assert base_assistant.state == AssistantState.GENERATING_OUTPUT

    # 3) Run again - LLM responds
    mock_resp = {
        'message': {
            'content': "LLM's answer to the user's question.",
            'tool_calls': None
        }
    }
    mock_ollama_chat.return_value = mock_resp
    base_assistant.run()

    # Verify final message from assistant
    assert base_assistant.chat_session.messages[-1].role == "assistant"
    assert base_assistant.chat_session.messages[-1].content == "LLM's answer to the user's question."
    assert base_assistant.state == AssistantState.WAITING_USER_INPUT

def test_run_with_tool_calls(base_assistant, mock_ollama_chat):
    """Test run method when the LLM requests a tool call."""
    # Register a fake tool function
    def fake_tool(x: int) -> int:
        """A dummy tool that just returns x+1."""
        return x + 1
    base_assistant.register_tool(fake_tool)

    # Step 1: Simulate the LLM returning a message that includes a tool call
    mock_resp = {
        'message': {
            'content': None,
            'tool_calls': [{
                'function': {
                    'name': 'fake_tool',
                    'arguments': {"x": 99}
                }
            }]
        }
    }
    mock_ollama_chat.return_value = mock_resp

    # The assistant is initially in GENERATING_OUTPUT, so run
    base_assistant.run()

    # We expect state = PROCESSING_TOOL_CALLS, and no new assistant messages
    assert base_assistant.state == AssistantState.PROCESSING_TOOL_CALLS
    assert len(base_assistant.chat_session.messages) == 0

    # Step 2: Now run again to process the tool call
    base_assistant.run()
    # The single tool call is executed. The output is appended as role "tool"
    assert len(base_assistant.chat_session.messages) == 1
    assert base_assistant.chat_session.messages[0].role == "tool"
    assert base_assistant.chat_session.messages[0].content == "100"
    assert base_assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS
