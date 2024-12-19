# tests/test_base_assistant.py

import json
import pytest
from unittest.mock import patch, MagicMock

from plotomatic.assistant.base_assistant import BaseChatAssistant
from plotomatic.assistant.states import AssistantState
from plotomatic.models.chat import Message, ChatSession, ToolCall, ROLE_SYSTEM, ROLE_TOOL, ROLE_ASSISTANT

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
def base_assistant(temp_storage_path, mock_ollama_client):
    """
    Creates a fresh instance of BaseChatAssistant with a temporary storage path.
    Uses deterministic settings and caching client for testing.
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
    assert 'set_properties' in base_assistant.available_tools
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

def test_questioning_state_for_creative_write(base_assistant, mock_ollama_chat):
    """Test that creative_write tool triggers questioning state"""
    
    # First response: creative write tool call
    mock_ollama_chat.return_value = {
        'message': {
            'content': None,
            'tool_calls': [{
                'function': {
                    'name': 'creative_write',
                    'arguments': {
                        'prompt': 'Write a story',
                        'system_context': '',
                        'story_context': ''
                    }
                }
            }]
        }
    }
    
    # Initial run to get tool call
    base_assistant.run()
    assert base_assistant.state == AssistantState.PROCESSING_TOOL_CALLS
    
    # Second response: tool execution result
    mock_ollama_chat.return_value = {
        'message': {
            'content': 'Generated creative content',
            'tool_calls': None
        }
    }
    
    # Run to execute tool
    base_assistant.run()
    
    # Should transition to questioning state since creative_write needs_questioning=True
    assert base_assistant.state == AssistantState.QUESTIONING_TOOL_OUTPUT
    
    # Third response: questioning about the output
    mock_ollama_chat.return_value = {
        'message': {
            'content': 'How do you feel about this content? Is the style and tone what you were looking for?',
            'tool_calls': None
        }
    }
    
    # Run to process questioning
    base_assistant.run()
    
    # Should now be waiting for user input
    assert base_assistant.state == AssistantState.WAITING_USER_INPUT
    
    # Verify messages flow
    messages = base_assistant.chat_session.messages
    assert any(m.role == ROLE_TOOL and 'Generated creative content' in m.content for m in messages)
    assert any(m.role == ROLE_ASSISTANT and 'How do you feel about this content?' in m.content for m in messages)

def test_no_questioning_for_set_properties(base_assistant, mock_ollama_chat):
    """Test that set_properties tool skips questioning state"""
    
    # First response: set_properties tool call
    mock_ollama_chat.return_value = {
        'message': {
            'content': None,
            'tool_calls': [{
                'function': {
                    'name': 'set_properties',
                    'arguments': {
                        'properties': {
                            'title': 'Test Title'
                        }
                    }
                }
            }]
        }
    }
    
    # Initial run to get tool call
    base_assistant.run()
    assert base_assistant.state == AssistantState.PROCESSING_TOOL_CALLS
    
    # Second response: tool execution result
    mock_ollama_chat.return_value = {
        'message': {
            'content': 'Properties updated',
            'tool_calls': None
        }
    }
    
    # Run to execute tool
    base_assistant.run()
    
    # Should skip questioning and go straight to waiting
    assert base_assistant.state == AssistantState.WAITING_USER_INPUT
    
    # Verify messages flow
    messages = base_assistant.chat_session.messages
    assert any(m.role == ROLE_TOOL and 'Set `title`' in m.content for m in messages)
    assert any(m.role == ROLE_ASSISTANT and 'Properties updated' in m.content for m in messages)

def test_tool_metadata_needs_questioning(base_assistant):
    """Test that tool metadata correctly tracks needs_questioning flag"""
    
    # Check creative_write has needs_questioning=True
    creative_write_metadata = base_assistant.get_tool_metadata('creative_write')
    assert creative_write_metadata.needs_questioning is True
    
    # Check set_properties has needs_questioning=False
    set_properties_metadata = base_assistant.get_tool_metadata('set_properties')
    assert set_properties_metadata.needs_questioning is False
    
    # Test custom tool with needs_questioning
    @base_assistant.tool(needs_questioning=True)
    def custom_tool():
        """Test tool"""
        return "test"
        
    base_assistant.register_tool(custom_tool)
    custom_metadata = base_assistant.get_tool_metadata('custom_tool')
    assert custom_metadata.needs_questioning is True

def test_questioning_prompt_content(base_assistant, mock_ollama_chat):
    """Test that questioning state uses appropriate prompt"""
    
    # Setup: Get to questioning state via creative_write
    mock_ollama_chat.return_value = {
        'message': {
            'content': None,
            'tool_calls': [{
                'function': {
                    'name': 'creative_write',
                    'arguments': {
                        'prompt': 'Write a story',
                        'system_context': '',
                        'story_context': ''
                    }
                }
            }]
        }
    }
    
    base_assistant.run()  # Get tool call
    
    mock_ollama_chat.return_value = {
        'message': {
            'content': 'Generated content',
            'tool_calls': None
        }
    }
    
    base_assistant.run()  # Execute tool -> questioning state
    assert base_assistant.state == AssistantState.QUESTIONING_TOOL_OUTPUT
    
    # Capture the call to ollama.chat in questioning state
    base_assistant.run()
    
    # Get the last call to mock_ollama_chat
    last_call = mock_ollama_chat.call_args
    messages = last_call[1]['messages']
    
    # Verify system message contains expected questioning prompts
    system_message = next(m for m in messages if m['role'] == 'system')
    assert 'Review the previous tool output' in system_message['content']
    assert 'style and tone' in system_message['content']
    assert 'key elements' in system_message['content']
    assert 'length and detail' in system_message['content']
