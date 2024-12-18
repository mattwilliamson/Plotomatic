import os
from datetime import datetime
import traceback

from plotomatic.assistant.story_overview_assistant import StoryOverviewAssistant
from plotomatic.assistant.states import AssistantState
from plotomatic.models.story import Story
from plotomatic.models.chat import ChatSession
from conftest import CachingTransport
from devtools import debug

class TestStep:
    step_counter = 0  # Class variable to track steps

    def __init__(self, description, should_run=True, assistant=None):
        self.description = description
        self.should_run = should_run
        self.assistant = assistant
        TestStep.step_counter += 1
        self.step_number = TestStep.step_counter

    def __enter__(self):
        print("\n\n\n\n")
        print("#" * 100)
        print(f"\nSTEP {self.step_number} START: '{self.description}'")
        print(f"Assistant state start: {self.assistant.state}")
        if self.should_run:
            self.assistant.run()

        print("\nChat Session Messages:")
        print(self.assistant.chat_session.model_dump_json(indent=2))

        print("\nPrepended Messages:")
        for msg in self.assistant.prepended_messages:
            print(f"\n{msg.role}: {msg.content}")
            
        print(f"\nTool Calls: {self.assistant.tool_calls}")

        print(f"Story: {self.assistant.story.model_dump_json(indent=2)}")
    

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("\nLast message:")
        if len(self.assistant.chat_session.messages) > 0:
            print(self.assistant.chat_session.messages[-1])
        print(f"\nAssistant state end: {self.assistant.state}")

        # Add detailed assistant info printing on failure
        if exc_type is not None:
            print("\n" + "!" * 100)
            print("TEST FAILED! Assistant state dump:")
            print("!" * 100)

            print("\nTraceback:")
            traceback.print_exception(exc_type, exc_val, exc_tb)

            print("\n" + "!" * 100)

        print(f"\nSTEP {self.step_number} END: '{self.description}'")
        print("#" * 100)
        print("\n\n\n\n")

        return False

def test_story_overview_assistant_full_flow(temp_project_dir, ollama_cache_dir, monkeypatch):
    """Test the full flow using real Story objects and cached Ollama calls"""
    
    # Check if we should delete the cache
    should_delete_cache = os.environ.get('DELETE_OLLAMA_CACHE', '').lower() in ('true', '1', 'yes')
    if should_delete_cache and ollama_cache_dir.exists():
        import shutil
        shutil.rmtree(ollama_cache_dir)
        ollama_cache_dir.mkdir(parents=True)

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

    # Save initial story using Story's built-in method
    story.save_to_directory(project_path)

    # Initialize assistant with deterministic settings
    assistant = StoryOverviewAssistant.load_for_project(
        project_path,
        agent_temperature=0.0,
        creative_temperature=0.0,
        agent_seed=0,
        creative_seed=0
    )
    assistant.story = story

    # Create initial chat session
    assistant.chat_session = ChatSession(
        project=str(project_path),
        messages=[]
    )

    # Patch Ollama client to use caching transport
    monkeypatch.setattr('httpx.HTTPTransport', lambda: CachingTransport(ollama_cache_dir))

    # Check initial state which is llm generating output to greet user
    assert assistant.state == AssistantState.GENERATING_OUTPUT

    # Round 1

    with TestStep("First run should greet and ask what kind of story you want to write", assistant=assistant):
        assert len(assistant.chat_session.messages) == 1
        m = assistant.chat_session.messages[-1]
        assert m.role == "assistant"
        assert "hello" in m.content.lower()
        assert "tell me what kind of story you're interested in creating" in m.content.lower()
        assert assistant.state == AssistantState.WAITING_USER_INPUT
    
    with TestStep("User requests science fiction", assistant=assistant):
        assistant.send_message("How about science fiction")
        assert len(assistant.chat_session.messages) == 2
        m = assistant.chat_session.messages[-1]
        assert m.role == "user"
        assert "How about science fiction" in m.content
        assert assistant.state == AssistantState.GENERATING_OUTPUT

    with TestStep("LLM returns set_property tool", assistant=assistant):
        assert len(assistant.prepended_messages) == 2
        m = assistant.prepended_messages[1]
        assert "Empty Fields That Need Attention:\n- author" in m.content
        assert assistant.tool_calls is not None
        assert len(assistant.tool_calls) == 1
        assert assistant.tool_calls[0].name == "set_property"
        assert assistant.tool_calls[0].arguments == {"property_name": "genre", "value": "Science Fiction"}
        assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS

    with TestStep("LLM Calls set_property tool", assistant=assistant):
        assert len(assistant.chat_session.messages) == 3
        m = assistant.chat_session.messages[-1]
        assert m.role == "tool"
        assert "**Set `genre`** to: `'Science Fiction'`" in m.content
        # TODO: Check that the show_user = False
        assert assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS

    with TestStep("Call LLM With Tool Output that set_property tool returns", assistant=assistant):
        assert len(assistant.chat_session.messages) == 4
        m = assistant.chat_session.messages[-1]
        assert m.role == "assistant"
        assert len(assistant.tool_calls) == 0
        assert "science fiction" in m.content.lower()
        # assert "what kind of setting are you envisioning" in m.content.lower()
        assert "we've set the genre of our story to science fiction" in m.content.lower()
        assert assistant.state == AssistantState.WAITING_USER_INPUT
        assert assistant.story.genre.lower() == "science fiction"
    # Round 2

    with TestStep("User requests random story", assistant=assistant):
        assistant.send_message("Just give me a completely random story")
        assert len(assistant.chat_session.messages) == 5
        m = assistant.chat_session.messages[-1]
        assert m.role == "user"
        assert assistant.state == AssistantState.GENERATING_OUTPUT

    with TestStep("LLM returns creative_write tool calls", assistant=assistant):
        assert len(assistant.chat_session.messages) == 5
        m = assistant.chat_session.messages[1]
        assert assistant.tool_calls is not None
        assert len(assistant.tool_calls) == 1
        assert assistant.tool_calls[0].name == "creative_write"
        assert assistant.tool_calls[0].arguments == {
            "prompt": "Write a completely random story", 
            "system_context": "", 
            "story_context": ""
        }
        assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS

    with TestStep("LLM Calls creative_write tool", assistant=assistant):
        assert len(assistant.chat_session.messages) == 6
        m = assistant.chat_session.messages[-1]
        assert m.role == "tool"
        assert "In the depths of a distant galaxy" in m.content
        assert len(m.content) > 100
        # TODO: Check that the show_user = False
        assert assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS

    with TestStep("Call LLM With Tool Output that creative_write tool returns", assistant=assistant):
        assert len(assistant.chat_session.messages) == 7
        m = assistant.chat_session.messages[-1]
        assert m.role == "assistant"
        assert len(assistant.tool_calls) == 0
        assert "science fiction" in m.content.lower()
        assert "decided" in m.content.lower()
        assert assistant.state == AssistantState.WAITING_USER_INPUT
        assert assistant.story.genre.lower() == "science fiction"

    # Round 3

    with TestStep("User accepts the generated story", assistant=assistant):
        assistant.send_message("That looks great. let's start there.")
        assert len(assistant.chat_session.messages) == 8
        m = assistant.chat_session.messages[-1]
        assert m.role == "user"
        assert assistant.state == AssistantState.GENERATING_OUTPUT

    # Tool calls to set the story overview and other properties
    with TestStep("LLM returns set_property tool calls", assistant=assistant):
        assert len(assistant.chat_session.messages) == 8
        m = assistant.chat_session.messages[1]
        assert assistant.tool_calls is not None
        assert len(assistant.tool_calls) == 1
        assert assistant.tool_calls[0].name == "set_property"
        assert assistant.tool_calls[0].arguments["property_name"] == "plot_overview"
        # Make sure the value is more than 50 characters
        assert len(assistant.tool_calls[0].arguments["value"]) > 50
        assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS

    with TestStep("LLM Calls set_property tool", assistant=assistant):
        assert len(assistant.chat_session.messages) == 9
        m = assistant.chat_session.messages[-1]
        assert m.role == "tool"
        assert "set_property" in m.content
        assert "plot_overview" in m.content
        assert assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS


    with TestStep("Call LLM With Tool Output that set_property tool returns", assistant=assistant):
        assert len(assistant.chat_session.messages) == 10
        m = assistant.chat_session.messages[-1]
        assert m.role == "assistant"
        assert len(assistant.tool_calls) == 0
        assert "science fiction" in m.content.lower()
        assert "this gives us a solid foundation" in m.content.lower()
        assert assistant.state == AssistantState.WAITING_USER_INPUT
        assert assistant.story.genre.lower() == "science fiction"
        # Add checks for plot_overview
        assert assistant.story.plot_overview is not None
        assert len(assistant.story.plot_overview) > 50

    # Round 4

    with TestStep("User requests to add a character", assistant=assistant):
        assistant.send_message("Add a character")
        assert len(assistant.chat_session.messages) == 11
        m = assistant.chat_session.messages[-1]
        assert m.role == "user"
        assert assistant.state == AssistantState.GENERATING_OUTPUT

    # Tool calls to set the story overview and other properties
    with TestStep("LLM returns set_property tool calls", assistant=assistant):
        assert len(assistant.chat_session.messages) == 8
        m = assistant.chat_session.messages[1]
        assert assistant.tool_calls is not None
        assert len(assistant.tool_calls) == 1
        assert assistant.tool_calls[0].name == "set_property"
        assert assistant.tool_calls[0].arguments["property_name"] == "plot_overview"
        # Make sure the value is more than 50 characters
        assert len(assistant.tool_calls[0].arguments["value"]) > 50
        assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS
