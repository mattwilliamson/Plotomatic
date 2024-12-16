import json
import pytest
import hashlib
from pathlib import Path
from datetime import datetime
import httpx

from plotomatic.assistant.story_overview_assistant import StoryOverviewAssistant
from plotomatic.assistant.states import AssistantState
from plotomatic.models.story import Story
from plotomatic.models.chat import ChatSession
from plotomatic.assistant.tools import tools

class CachingTransport(httpx.HTTPTransport):
    """HTTP transport that caches responses"""
    def __init__(self, cache_dir: Path):
        super().__init__()
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle request with caching"""
        # Create cache key from request details
        cache_key = hashlib.md5(
            f"{request.method}{request.url}{request.content}".encode()
        ).hexdigest()
        
        cache_file = self.cache_dir / f"{cache_key}.json"

        # Check cache first
        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                return httpx.Response(200, content=f.read())

        # If not in cache, make real request and cache response
        response = super().handle_request(request)
        
        with open(cache_file, 'wb') as f:
            f.write(response.content)
            
        return response

@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory for testing"""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir

@pytest.fixture
def ollama_cache_dir(tmp_path):
    """Create a temporary directory for Ollama response caching"""
    cache_dir = tmp_path / "ollama_cache"
    cache_dir.mkdir()
    return cache_dir

def test_story_overview_assistant_full_flow(temp_project_dir, ollama_cache_dir, monkeypatch):
    """Test the full flow using real Story objects and cached Ollama calls"""
    # Set up project structure
    project_path = temp_project_dir
    
    # Create initial story
    story = Story(
        title="",
        genre="",
        plot_overview="",
        created_at=datetime.now().isoformat(),
        modified_at=datetime.now().isoformat()
    )

    # Save initial story
    story_file = project_path / "story.json"
    with open(story_file, "w") as f:
        json.dump(story.model_dump(), f)

    # Initialize assistant
    assistant = StoryOverviewAssistant.load_for_project(project_path)
    assistant.story = story

    # Create initial chat session
    assistant.chat_session = ChatSession(
        project=str(project_path),
        messages=[]
    )

    # Patch Ollama client to use caching transport
    monkeypatch.setattr('httpx.HTTPTransport', lambda: CachingTransport(ollama_cache_dir))

    # First run - should greet and ask about empty title
    assistant.run()
    
    assert len(assistant.chat_session.messages) == 1
    assert assistant.chat_session.messages[0].role == "assistant"
    assert "title is currently empty" in assistant.chat_session.messages[0].content
    assert assistant.state == AssistantState.WAITING_USER_INPUT

    # Comment out remaining test steps for now
    """
    # User requests title help
    assistant.send_message("Yes, please help me with a title. I want something epic.")
    assert len(assistant.chat_session.messages) == 2
    assert assistant.chat_session.messages[1].role == "user"
    assert assistant.state == AssistantState.GENERATING_OUTPUT

    # Run assistant to process request
    assistant.run()
    
    # Verify the story was updated
    assert assistant.story.title == "The Epic Quest"
    
    # Verify the changes were saved
    with open(story_file) as f:
        saved_story = Story(**json.load(f))
        assert saved_story.title == "The Epic Quest"

    # Verify final state
    assert assistant.state == AssistantState.WAITING_USER_INPUT
    
    # Check that messages were saved
    state_file = project_path / "story_overview_state.json"
    assert state_file.exists()
    with open(state_file) as f:
        saved_state = json.load(f)
        assert len(saved_state["chat_session"]["messages"]) >= 3  # Initial + user + response
    """

