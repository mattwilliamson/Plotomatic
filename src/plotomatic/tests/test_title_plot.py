import pytest
from unittest.mock import Mock, patch
import streamlit as st
from plotomatic.pages.title_and_plot import (
    chat_agent,
    process_message,
)
from plotomatic.models.chat import Message, ChatSession
import json

@pytest.fixture
def mock_streamlit():
    """Mock streamlit functions and session state"""
    with patch('streamlit.chat_message') as mock_chat_message, \
         patch('streamlit.markdown') as mock_markdown, \
         patch('streamlit.columns') as mock_columns, \
         patch('streamlit.button') as mock_button, \
         patch('streamlit.session_state') as mock_session_state:
        
        # Setup mock columns
        mock_col = Mock()
        mock_columns.return_value = [mock_col]
        
        # Setup session state
        mock_session_state.messages = []
        mock_session_state.story = Mock()
        mock_session_state.pm = Mock()
        mock_session_state.debug_logs = []
        
        yield {
            'chat_message': mock_chat_message,
            'markdown': mock_markdown,
            'columns': mock_columns,
            'button': mock_button,
            'session_state': mock_session_state,
            'col': mock_col
        }

@pytest.fixture
def mock_ollama():
    """Mock ollama client responses"""
    with patch('plotomatic.llm_models.ollama_client') as mock_client:
        yield mock_client

def test_show_user_options_display(mock_streamlit, mock_ollama):
    """Test that show_user_options tool calls display buttons correctly"""
    # Setup test messages with show_user_options
    messages = [{
        "role": "assistant",
        "content": "",
        "tool_calls": [{
            "function": {
                "name": "show_user_options",
                "arguments": {
                    "prompt": "Test prompt",
                    "options": ["Option 1", "Option 2"]
                }
            }
        }]
    }]
    
    # Call chat_agent
    chat_agent(messages)
    
    # Verify buttons were displayed
    mock_streamlit['markdown'].assert_any_call("**Test prompt**")
    mock_streamlit['columns'].assert_called_once_with(2)  # 2 options = 2 columns
    mock_streamlit['col'].button.assert_any_call("Option 1", use_container_width=True)
    mock_streamlit['col'].button.assert_any_call("Option 2", use_container_width=True)

def test_user_option_selection(mock_streamlit, mock_ollama):
    """Test handling of user selecting an option"""
    # Setup messages with show_user_options
    messages = [{
        "role": "assistant",
        "content": "",
        "tool_calls": [{
            "function": {
                "name": "show_user_options",
                "arguments": {
                    "prompt": "Test prompt",
                    "options": ["Option 1", "Option 2"]
                }
            }
        }]
    }]
    
    # Simulate button click by returning True
    mock_streamlit['col'].button.return_value = True
    
    # Call chat_agent
    chat_agent(messages)
    
    # Verify message was added and chat session was saved
    assert len(mock_streamlit['session_state'].messages) > 0
    mock_streamlit['session_state'].pm.save_chat.assert_called_once()

def test_chat_agent_processing(mock_streamlit, mock_ollama):
    """Test chat agent processing of messages"""
    # Setup mock ollama response
    mock_response = Mock()
    mock_response.message.content = "Test response"
    mock_response.message.tool_calls = None
    mock_ollama.chat.return_value = mock_response
    
    # Call chat_agent with test message
    messages = [{"role": "user", "content": "Test message"}]
    chat_agent(messages)
    
    # Verify ollama was called and response was processed
    mock_ollama.chat.assert_called_once()
    assert len(mock_streamlit['session_state'].messages) > 0

def test_empty_content_handling(mock_streamlit, mock_ollama):
    """Test handling of messages with empty content but tool calls"""
    # Setup mock response with empty content but tool calls
    mock_response = Mock()
    mock_response.message.content = ""
    mock_response.message.tool_calls = [{
        "function": {
            "name": "show_user_options",
            "arguments": {
                "prompt": "Test prompt",
                "options": ["Option 1"]
            }
        }
    }]
    mock_ollama.chat.return_value = mock_response
    
    # Call chat_agent
    messages = [{"role": "user", "content": "Test"}]
    chat_agent(messages)
    
    # Verify message was added despite empty content
    assert len(mock_streamlit['session_state'].messages) > 0
    assert mock_streamlit['session_state'].messages[-1]["tool_calls"] is not None

def test_chat_session_persistence(mock_streamlit, mock_ollama):
    """Test that chat sessions are properly saved to disk"""
    # Setup mock response
    mock_response = Mock()
    mock_response.message.content = "Test response"
    mock_response.message.tool_calls = None
    mock_ollama.chat.return_value = mock_response
    
    # Call chat_agent
    messages = [{"role": "user", "content": "Test"}]
    chat_agent(messages)
    
    # Verify chat session was saved
    mock_streamlit['session_state'].pm.save_chat.assert_called_once()
    saved_messages = mock_streamlit['session_state'].pm.save_chat.call_args[0][1].messages
    assert len(saved_messages) > 0
    assert isinstance(saved_messages[0], Message) 