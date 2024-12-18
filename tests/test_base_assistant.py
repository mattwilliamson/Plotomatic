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
    Uses deterministic settings for testing.
    """
    assistant = BaseChatAssistant(
        storage_path=temp_storage_path,
        agent_temperature=0.0,  # Deterministic for testing
        creative_temperature=0.0,  # Deterministic for testing
        agent_seed=0,  # Fixed seed for testing
        creative_seed=0,  # Fixed seed for testing
    )
    return assistant

def test_base_assistant_initial_state(base_assistant):
    """
    Test that the BaseChatAssistant initializes with correct default values.
    """
    assert base_assistant.state == base_assistant.STATE_GENERATING_OUTPUT
    assert len(base_assistant.chat_session.messages) == 0
    assert base_assistant.tool_calls == []
    assert base_assistant.quick_responses == []
    assert base_assistant.system_prompt in base_assistant.BASE_SYSTEM_PROMPT
    assert 'set_property' in base_assistant.available_tools
    assert 'creative_write' in base_assistant.available_tools

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
    base_assistant.register_tool(fake_tool)  # Register function directly

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
    # The tool call execution adds two messages: start and result
    assert len(base_assistant.chat_session.messages) == 2
    
    # Check execution start message
    assert base_assistant.chat_session.messages[0].role == "tool"
    assert base_assistant.chat_session.messages[0].content == "Executing fake_tool..."
    
    # Check result message
    assert base_assistant.chat_session.messages[1].role == "tool"
    assert base_assistant.chat_session.messages[1].content == "100"
    
    assert base_assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS

    # Mock final response after tool execution
    mock_ollama_chat.return_value = {
        'message': {
            'content': "Tool execution complete",
            'tool_calls': None
        }
    }

    # Step 3: Process the tool output
    base_assistant.run()
    assert base_assistant.state == AssistantState.WAITING_USER_INPUT

def test_current_tool_tracking(base_assistant, mock_ollama_chat):
    """Test that the assistant properly tracks the currently executing tool."""
    
    # Register a test tool
    def test_tool(x: int) -> int:
        return x + 1
    base_assistant.register_tool("test_tool", test_tool)
    
    # Simulate LLM returning a tool call
    mock_ollama_chat.return_value = {
        'message': {
            'content': None,
            'tool_calls': [{
                'function': {
                    'name': 'test_tool',
                    'arguments': {"x": 1}
                }
            }]
        }
    }
    
    # Initial state - no current tool
    assert base_assistant.get_current_tool() is None
    
    # Run to get tool calls
    base_assistant.run()
    assert base_assistant.state == AssistantState.PROCESSING_TOOL_CALLS
    assert base_assistant.get_current_tool() is None  # Still None before execution
    
    # Run to execute tool
    base_assistant.run()
    # Tool should be done now, so current_tool should be None again
    assert base_assistant.get_current_tool() is None
    assert base_assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS

def test_tool_execution_status_in_messages(base_assistant, mock_ollama_chat):
    """Test that tool execution status is properly reflected in messages."""
    
    # Register test tools
    def tool1(x: int) -> int:
        # Add a check for current tool during execution
        current = base_assistant.get_current_tool()
        assert current is not None
        assert current.name == "tool1"
        return x + 1
        
    def tool2(y: int) -> int:
        # Add a check for current tool during execution
        current = base_assistant.get_current_tool()
        assert current is not None
        assert current.name == "tool2"
        return y * 2
        
    base_assistant.register_tool(tool1)  # Register function directly
    base_assistant.register_tool(tool2)  # Register function directly
    
    # First response: return tool calls
    mock_ollama_chat.return_value = {
        'message': {
            'content': None,
            'tool_calls': [
                {
                    'function': {
                        'name': 'tool1',
                        'arguments': {"x": 1}
                    }
                },
                {
                    'function': {
                        'name': 'tool2',
                        'arguments': {"y": 2}
                    }
                }
            ]
        }
    }
    
    # Run to get tool calls
    base_assistant.run()
    assert len(base_assistant.tool_calls) == 2
    assert base_assistant.get_current_tool() is None  # No tool executing yet
    
    # Run to execute first tool
    base_assistant.run()
    # Tool1 execution is checked inside the tool function
    assert base_assistant.get_current_tool() is None  # Tool1 finished
    
    # Run to execute second tool
    base_assistant.run()
    # Tool2 execution is checked inside the tool function
    assert base_assistant.get_current_tool() is None  # Tool2 finished
    
    # Mock final response after tool execution
    mock_ollama_chat.return_value = {
        'message': {
            'content': "All tools executed successfully",
            'tool_calls': None
        }
    }
    
    # Final run to process outputs
    base_assistant.run()
    assert base_assistant.get_current_tool() is None
    assert base_assistant.state == AssistantState.WAITING_USER_INPUT  # Now in waiting state
    
    # Verify all messages are present
    messages = base_assistant.chat_session.messages
    assert len(messages) >= 4  # At least 4 messages (2 tool starts, 2 tool results)
    assert any(m.content == "Executing tool1..." for m in messages)
    assert any(m.content == "2" for m in messages)  # tool1 result
    assert any(m.content == "Executing tool2..." for m in messages)
    assert any(m.content == "4" for m in messages)  # tool2 result

def test_temperature_and_seed_settings():
    """Test that temperature and seed settings can be configured."""
    # Test defaults
    assistant = BaseChatAssistant()
    assert assistant.agent_temperature == BaseChatAssistant.AGENT_TEMPERATURE
    assert assistant.creative_temperature == BaseChatAssistant.CREATIVE_TEMPERATURE
    assert assistant.agent_seed == BaseChatAssistant.AGENT_SEED
    assert assistant.creative_seed == BaseChatAssistant.CREATIVE_SEED
    
    # Test override all settings
    test_assistant = BaseChatAssistant(
        agent_temperature=0.0,
        creative_temperature=0.0,
        agent_seed=0,
        creative_seed=0
    )
    assert test_assistant.agent_temperature == 0.0
    assert test_assistant.creative_temperature == 0.0
    assert test_assistant.agent_seed == 0
    assert test_assistant.creative_seed == 0
