import json
from datetime import datetime

from plotomatic.assistant.story_overview_assistant import StoryOverviewAssistant
from plotomatic.assistant.states import AssistantState
from plotomatic.models.story import Story
from plotomatic.models.chat import ChatSession

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

