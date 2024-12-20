import pytest
from datetime import datetime
from pathlib import Path
import json
import os

from plotomatic.assistant.base_assistant import BaseChatAssistant
from plotomatic.models.chat import (
    Message, 
    ChatSession, 
    ToolCall, 
    ROLE_SYSTEM,
    ROLE_USER,
    ROLE_ASSISTANT,
    ROLE_TOOL
)
from plotomatic.assistant.states import AssistantState
from plotomatic.models import Story

@pytest.fixture
def clean_assistant(tmp_path):
    """Fixture to provide a clean BaseChatAssistant instance for each test."""
    # Create a temporary storage path
    storage_path = tmp_path / "test_assistant.json"
    
    # Remove any existing storage file
    if storage_path.exists():
        storage_path.unlink()
        
    # Create new assistant with clean state
    assistant = BaseChatAssistant(storage_path=str(storage_path))
    
    # Clear any existing messages
    assistant.chat_session = ChatSession(project="", messages=[])
    
    return assistant

def test_init_default(clean_assistant):
    """Test default initialization of BaseChatAssistant."""
    assistant = clean_assistant
    
    assert assistant.state == AssistantState.GENERATING_OUTPUT
    assert isinstance(assistant.chat_session, ChatSession)
    assert len(assistant.chat_session.messages) == 0
    assert len(assistant.tool_calls) == 0
    assert len(assistant.quick_responses) == 0
    assert assistant.agent_temperature == 0.5
    assert assistant.creative_temperature == 0.8

def test_init_with_custom_params(tmp_path):
    """Test initialization with custom parameters."""
    storage_path = tmp_path / "custom_storage.json"
    assistant = BaseChatAssistant(
        storage_path=str(storage_path),
        system_prompt="Custom prompt",
        agent_temperature=0.7,
        creative_temperature=0.9,
        agent_seed=42,
        creative_seed=123
    )
    
    assert assistant.storage_path == str(storage_path)
    assert assistant.system_prompt == "Custom prompt"
    assert assistant.agent_temperature == 0.7
    assert assistant.creative_temperature == 0.9
    assert assistant.agent_seed == 42
    assert assistant.creative_seed == 123

def test_send_message(clean_assistant):
    """Test sending a message to the assistant."""
    assistant = clean_assistant
    
    assistant.send_message("Hello")
    
    assert len(assistant.chat_session.messages) == 1
    msg = assistant.chat_session.messages[0]
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.show_user is True
    assert assistant.state == AssistantState.GENERATING_OUTPUT

def test_quick_responses(clean_assistant):
    """Test quick response management."""
    assistant = clean_assistant
    
    # Test setting quick responses
    responses = ["Yes", "No", "Maybe"]
    assistant.set_quick_responses(responses)
    assert assistant.quick_responses == responses
    
    # Test clearing quick responses
    assistant.clear_quick_responses()
    assert len(assistant.quick_responses) == 0

def test_tool_registration(clean_assistant):
    """Test tool registration functionality."""
    assistant = clean_assistant
    
    # Test function to register
    @BaseChatAssistant.tool(emoji="🔧", description="Test tool")
    def test_tool(x: int) -> str:
        return f"Result: {x}"
    
    # Register the tool
    assistant.register_tool(test_tool)
    
    assert "test_tool" in assistant.available_tools
    metadata = assistant.get_tool_metadata("test_tool")
    assert metadata.emoji == "🔧"
    assert metadata.description == "Test tool"

def test_tool_registration_by_name(clean_assistant):
    """Test registering built-in tools by name."""
    assistant = clean_assistant
    
    # Register built-in tool
    assistant.register_tool("set_properties")
    
    assert "set_properties" in assistant.available_tools
    metadata = assistant.get_tool_metadata("set_properties")
    assert metadata.emoji == "✏️"

def test_state_persistence(tmp_path):
    """Test saving and loading assistant state."""
    storage_path = tmp_path / "test_storage.json"
    
    # Create assistant and add some state
    assistant = BaseChatAssistant(storage_path=str(storage_path))
    assistant.chat_session = ChatSession(project="", messages=[])  # Start clean
    assistant.send_message("Test message")
    assistant.set_quick_responses(["Yes", "No"])
    assistant.save_state()
    
    # Create new assistant with same storage path
    new_assistant = BaseChatAssistant(storage_path=str(storage_path))
    
    # Check if state was restored
    assert len(new_assistant.chat_session.messages) == 1
    assert new_assistant.chat_session.messages[0].content == "Test message"
    assert new_assistant.quick_responses == ["Yes", "No"]

def test_ephemeral_messages(clean_assistant):
    """Test adding ephemeral messages."""
    assistant = clean_assistant
    
    assistant.add_ephemeral_message("system", "Temporary instruction")
    
    assert len(assistant.chat_session.messages) == 1
    msg = assistant.chat_session.messages[0]
    assert msg.role == "system"
    assert msg.content == "Temporary instruction"
    assert msg.ephemeral is True
    assert msg.show_user is False

def test_status_management(clean_assistant):
    """Test status message management."""
    assistant = clean_assistant
    
    # Set status
    assistant.set_status("success", "Operation completed")
    status = assistant.get_and_clear_status()
    
    assert status == ("success", "Operation completed")
    assert assistant.get_and_clear_status() is None  # Status should be cleared

def test_get_current_instance(clean_assistant):
    """Test getting current assistant instance."""
    assistant = clean_assistant
    
    current = BaseChatAssistant.get_current()
    assert current is assistant

    with pytest.raises(RuntimeError):
        BaseChatAssistant._current_instance = None
        BaseChatAssistant.get_current()

def test_llm_options(clean_assistant):
    """Test LLM options generation."""
    assistant = clean_assistant
    assistant.agent_temperature = 0.7
    assistant.agent_seed = 42
    
    options = assistant._get_llm_options(temperature=0.8, seed=123)
    
    assert options['temperature'] == 0.8
    assert options['seed'] == 123
    assert options['num_ctx'] == 12000
    assert options['num_predict'] == 2000

def test_tool_execution(clean_assistant):
    """Test tool execution flow."""
    assistant = clean_assistant
    
    # Register a test tool
    @BaseChatAssistant.tool(emoji="🔧", description="Test tool")
    def test_tool(x: int) -> str:
        return f"Result: {x}"
    
    assistant.register_tool(test_tool)
    
    # Add a message with tool call
    assistant.chat_session.messages.append(Message(
        role="assistant",
        content="Let me help you with that.",
        tool_calls=[{
            "function": {
                "name": "test_tool",
                "arguments": {"x": 42}
            }
        }]
    ))
    
    # Process tool calls using proper ToolCall model
    assistant.tool_calls = [
        ToolCall(
            name="test_tool",
            arguments={"x": 42}
        )
    ]
    assistant.state = AssistantState.PROCESSING_TOOL_CALLS
    assistant._execute_tool_calls()
    
    # Check tool execution results
    assert len(assistant.chat_session.messages) > 0
    last_msg = assistant.chat_session.messages[-1]
    assert last_msg.role == "tool"
    assert "Result: 42" in last_msg.content

def test_parse_quick_responses(clean_assistant):
    """Test parsing quick responses from message content."""
    assistant = clean_assistant
    
    # Test basic quick responses
    content = "Here's my response\n\n---\n- Option 1\n- Option 2"
    cleaned, responses = assistant._parse_quick_responses(content)
    assert cleaned == "Here's my response"
    assert responses == ["Option 1", "Option 2"]
    
    # Test with multiple horizontal rules
    content = "Part 1\n---\nPart 2\n---\n- Option 1\n- Option 2"
    cleaned, responses = assistant._parse_quick_responses(content)
    assert cleaned == "Part 1\n---\nPart 2"
    assert responses == ["Option 1", "Option 2"]
    
    # Test with no quick responses
    content = "Just a regular message"
    cleaned, responses = assistant._parse_quick_responses(content)
    assert cleaned == "Just a regular message"
    assert responses == []
    
    # Test with horizontal rule but no valid list
    content = "Message\n---\nNot a list"
    cleaned, responses = assistant._parse_quick_responses(content)
    assert cleaned == "Message"
    assert responses == []

def test_llm_quick_responses(clean_assistant, monkeypatch):
    """Test LLM response handling with quick responses."""
    assistant = clean_assistant
    
    # Mock ollama response with quick responses
    mock_response = {
        'message': {
            'content': "Here's my response\n\n---\n- Yes\n- No\n- Maybe",
            'tool_calls': None
        }
    }
    
    def mock_chat(*args, **kwargs):
        return mock_response
    
    # Patch the ollama client
    monkeypatch.setattr(assistant._ollama_client, 'chat', mock_chat)
    
    # Call LLM
    assistant._call_llm()
    
    # Check that message was cleaned and quick responses were set
    assert len(assistant.chat_session.messages) == 1
    assert assistant.chat_session.messages[0].content == "Here's my response"
    assert assistant.quick_responses == ["Yes", "No", "Maybe"]
    assert assistant.state == AssistantState.WAITING_USER_INPUT

def test_llm_response_with_tool_calls_and_quick_responses(clean_assistant, monkeypatch):
    """Test LLM response handling with both tool calls and quick responses."""
    assistant = clean_assistant
    
    # Mock ollama response with both tool calls and quick responses
    mock_response = {
        'message': {
            'content': "Let me help with that\n\n---\n- Proceed\n- Cancel",
            'tool_calls': [{
                'function': {
                    'name': 'test_tool',
                    'arguments': {'x': 42}
                }
            }]
        }
    }
    
    def mock_chat(*args, **kwargs):
        return mock_response
    
    # Patch the ollama client
    monkeypatch.setattr(assistant._ollama_client, 'chat', mock_chat)
    
    # Call LLM
    assistant._call_llm()
    
    # Check that both message was cleaned and tool calls were processed
    assert len(assistant.chat_session.messages) == 1
    assert assistant.chat_session.messages[0].content == "Let me help with that"
    assert assistant.quick_responses == ["Proceed", "Cancel"]
    assert len(assistant.tool_calls) == 1
    assert assistant.tool_calls[0].name == "test_tool"
    assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS

def test_custom_system_prompt_preserves_quick_responses(tmp_path):
    """Test that custom system prompts still include quick response instructions."""
    storage_path = tmp_path / "test_assistant.json"
    custom_prompt = "You are a custom assistant."
    
    assistant = BaseChatAssistant(
        storage_path=str(storage_path),
        system_prompt=custom_prompt
    )
    
    # Get the system message
    system_message = next(msg for msg in assistant.get_prepended_messages() 
                         if msg.role == ROLE_SYSTEM)
    
    # Should use custom prompt
    assert system_message.content == custom_prompt
    
    # Create assistant without custom prompt
    default_assistant = BaseChatAssistant(storage_path=str(storage_path))
    system_message = next(msg for msg in default_assistant.get_prepended_messages() 
                         if msg.role == ROLE_SYSTEM)
    
    # Should include quick response instructions
    assert "quick response options" in system_message.content
    assert "markdown list" in system_message.content
