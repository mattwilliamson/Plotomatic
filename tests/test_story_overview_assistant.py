import os
from datetime import datetime
import traceback

from plotomatic.assistant.story_overview_assistant import StoryOverviewAssistant
from plotomatic.assistant.states import AssistantState
from plotomatic.models.story import Story
from plotomatic.models.chat import ChatSession
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
        print(f"Prepended messages: {len(self.assistant.prepended_messages)}")
        print(f"Chat session messages: {len(self.assistant.chat_session.messages)}")
        print(f"Quick responses: {self.assistant.quick_responses}")

        if self.should_run:
            self.assistant.run()

        print("\nChat Session Messages:")
        debug(self.assistant.chat_session)

        print("\nPrepended Messages:")
        debug(self.assistant.prepended_messages)
            
        debug(self.assistant.tool_calls)

        debug(self.assistant.story)

        print("\nQuick Responses after run:")
        debug(self.assistant.quick_responses)
    
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("\nLast message:")
        if len(self.assistant.chat_session.messages) > 0:
            debug(self.assistant.chat_session.messages[-1])
        print(f"\nAssistant state end: {self.assistant.state}")
        print(f"Quick responses end: {self.assistant.quick_responses}")

        # Add detailed assistant info printing on failure
        if exc_type is not None:
            print("\n" + "!" * 100)
            print("TEST FAILED! Assistant state dump:")
            print("!" * 100)

            print("\nTraceback:")
            traceback.print_exception(exc_type, exc_val, exc_tb)

            print("\nQuick Responses at failure:")
            debug(self.assistant.quick_responses)

            print("\n" + "!" * 100)

        print(f"\nSTEP {self.step_number} END: '{self.description}'")
        print("#" * 100)
        print("\n\n\n\n")

        return False

def test_story_overview_assistant_full_flow(temp_project_dir, monkeypatch):
    """Test the full flow using real Story objects and Ollama calls"""
    
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

    # Check initial state which is llm generating output to greet user
    assert assistant.state == AssistantState.GENERATING_OUTPUT

    # Round 1

    with TestStep("First run should greet and ask what kind of story you want to write", assistant=assistant):
        # assert len(assistant.chat_session.messages) == 1
        m = assistant.chat_session.messages[-1]
        assert m.role == "assistant"
        assert "hello" in m.content.lower() or "welcome" in m.content.lower()
        assert "creat" in m.content.lower()
        assert assistant.state == AssistantState.WAITING_USER_INPUT
        assert len(assistant.quick_responses) > 0
        assert "Science Fiction" in assistant.quick_responses
    
    with TestStep("User requests science fiction", assistant=assistant):
        assistant.send_message("How about science fiction")
        assert len(assistant.quick_responses) == 0
        # assert len(assistant.chat_session.messages) == 2
        m = assistant.chat_session.messages[-1]
        assert m.role == "user"
        assert "How about science fiction" in m.content
        assert assistant.state == AssistantState.GENERATING_OUTPUT

        

    with TestStep("LLM returns set_properties tool for genre", assistant=assistant):
        # assert len(assistant.prepended_messages) == 2
        m = assistant.prepended_messages[1]
        assert "Empty Fields That Need Attention:\n- author" in m.content
        assert assistant.tool_calls is not None
        assert len(assistant.tool_calls) == 1
        assert assistant.tool_calls[0].name == "set_properties"
        assert assistant.tool_calls[0].arguments == {'properties': {'genre': 'Science Fiction'}}
        assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS

    with TestStep("LLM Calls set_properties tool for genre", assistant=assistant):
        # assert len(assistant.chat_session.messages) == 5
        m = assistant.chat_session.messages[-1]
        assert m.role == "tool"
        assert "Set `genre`" in m.content
        # TODO: Check that the show_user = False
        assert assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS

    with TestStep("Call LLM With Tool Output that set_properties tool returns for genre", assistant=assistant):
        # assert len(assistant.chat_session.messages) == 6
        m = assistant.chat_session.messages[-1]
        assert m.role == "assistant"
        assert len(assistant.tool_calls) == 0
        assert "science fiction" in m.content.lower()
        # assert "what kind of setting are you envisioning" in m.content.lower()
        # assert "with the genre set to science fiction" in m.content.lower()
        assert assistant.state == AssistantState.WAITING_USER_INPUT
        assert assistant.story.genre.lower() == "science fiction"

    # Round 2


    with TestStep("User requests medium", assistant=assistant):
        assistant.send_message("How about a graphic novel")
        # assert len(assistant.chat_session.messages) == 2
        m = assistant.chat_session.messages[-1]
        assert m.role == "user"
        assert assistant.state == AssistantState.GENERATING_OUTPUT

    with TestStep("LLM returns set_properties tool for medium", assistant=assistant):
        # assert len(assistant.prepended_messages) == 2
        m = assistant.prepended_messages[1]
        assert assistant.tool_calls is not None
        assert len(assistant.tool_calls) == 1
        assert assistant.tool_calls[0].name == "set_properties"
        assert assistant.tool_calls[0].arguments == {'properties': {'medium': 'Graphic Novel'}}
        assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS

    with TestStep("LLM Calls set_properties tool for medium", assistant=assistant):
        # assert len(assistant.chat_session.messages) == 5
        m = assistant.chat_session.messages[-1]
        assert m.role == "tool"
        assert "Set `medium`" in m.content
        # TODO: Check that the show_user = False
        assert assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS

    with TestStep("Call LLM With Tool Output that set_properties tool returns for medium", assistant=assistant):
        # assert len(assistant.chat_session.messages) == 6
        m = assistant.chat_session.messages[-1]
        assert m.role == "assistant"
        assert len(assistant.tool_calls) == 0
        assert "graphic novel" in m.content.lower()
        # assert "what kind of setting are you envisioning" in m.content.lower()
        # assert "with the genre set to science fiction" in m.content.lower()
        assert assistant.state == AssistantState.WAITING_USER_INPUT
        assert assistant.story.medium.lower() == "graphic novel"







    with TestStep("User requests random story", assistant=assistant):
        assistant.send_message("Just write a completely random story.")
        # assert len(assistant.chat_session.messages) == 7
        m = assistant.chat_session.messages[-1]
        assert m.role == "user"
        assert assistant.state == AssistantState.GENERATING_OUTPUT

        

# Start of tool calls

    # Tool calls to set the story overview and other properties
    # with TestStep("LLM returns set_properties tool calls for themes", assistant=assistant):
    #     # assert len(assistant.chat_session.messages) == 8
    #     m = assistant.chat_session.messages[1]
    #     assert assistant.tool_calls is not None
    #     assert len(assistant.tool_calls) == 1
    #     assert assistant.tool_calls[0].name == "set_properties"
    #     assert "themes" in assistant.tool_calls[0].arguments["properties"]
    #     assert len(assistant.tool_calls[0].arguments["properties"]["themes"]) > 1
    #     assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS

    # with TestStep("set_properties tool result for themes", assistant=assistant):
    #     # assert len(assistant.chat_session.messages) == 9
    #     m = assistant.chat_session.messages[-1]
    #     assert m.role == "tool"
    #     assert "set_properties" in m.content
    #     assert "themes" in m.content
    #     assert assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS


    # with TestStep("LLM returns set_properties tool calls for motifs", assistant=assistant):
    #     m = assistant.chat_session.messages[1]
    #     assert assistant.tool_calls is not None
    #     assert len(assistant.tool_calls) == 1
    #     assert assistant.tool_calls[0].name == "set_properties"
    #     # assert "motifs" in assistant.tool_calls[0].arguments["properties"]
    #     # assert len(assistant.tool_calls[0].arguments["properties"]["motifs"]) > 1
    #     assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS
    #     # Check that all those properties have len > 0


    # with TestStep("set_properties tool result for fields", assistant=assistant):
    #     m = assistant.chat_session.messages[-1]
    #     assert m.role == "tool"
    #     assert "set_properties" in m.content
    #     assert len(assistant.story.author) > 0
    #     assert len(assistant.story.genre) > 0
    #     assert len(assistant.story.medium) > 0
    #     assert len(assistant.story.narrative_style) > 0
    #     assert len(assistant.story.time_period) > 0
    #     assert len(assistant.story.location) > 0
    #     assert len(assistant.story.conflict_type) > 0
    #     assert len(assistant.story.motifs) > 0
    #     assert assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS




# End of tool calls


    # End of Round 2

    with TestStep("LLM returns creative_write tool calls", assistant=assistant):
        # assert len(assistant.chat_session.messages) == 8
        """Write a completely random story"""
        m = assistant.chat_session.messages[1]
        assert assistant.tool_calls is not None
        assert len(assistant.tool_calls) == 1
        assert assistant.tool_calls[0].name == "creative_write"
        # assert assistant.tool_calls[0].arguments == {
        #     "prompt": "Write a completely random", 
        #     "system_context": "", 
        #     "story_context": ""
        # }
        assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS

    with TestStep("LLM Calls creative_write tool", assistant=assistant):
        """In the depths of a forgotten galaxy,..."""
        # assert len(assistant.chat_session.messages) == 9
        m = assistant.chat_session.messages[-1]
        assert m.role == "tool"
        assert "galaxy" in m.content
        assert len(m.content) > 100
        # TODO: Check that the show_user = False
        assert assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS

    # with TestStep("LLM handles creative_write tool output", assistant=assistant):
    #     # assert len(assistant.chat_session.messages) == 9
    #     m = assistant.chat_session.messages[-1]
    #     assert m.role == "tool"
    #     # assert "In the depths of a distant galaxy" in m.content
    #     assert len(m.content) > 100
    #     # TODO: Check that the show_user = False
    #     assert assistant.state == AssistantState.QUESTIONING_TOOL_OUTPUT

    # with TestStep("Call LLM With Tool Output that creative_write tool returns", assistant=assistant):
    #     # assert len(assistant.chat_session.messages) == 7
    #     """# Random Story\nHere's a completely random story for you:\nIn the depths of a forgotten galax..."""
    #     m = assistant.chat_session.messages[-1]
    #     assert m.role == "assistant"
    #     assert len(assistant.tool_calls) == 0
    #     assert "random story" in m.content.lower()
    #     assert len(m.content) < 100
    #     assert assistant.state == AssistantState.WAITING_USER_INPUT
    #     assert assistant.story.genre.lower() == "science fiction"

    # # Round 3

    # with TestStep("User accepts the generated story", assistant=assistant):
    #     assistant.send_message("That looks great. let's start there.")
    #     # assert len(assistant.chat_session.messages) == 8
    #     m = assistant.chat_session.messages[-1]
    #     assert m.role == "user"
    #     assert assistant.state == AssistantState.GENERATING_OUTPUT

    # Tool calls to set the story overview and other properties
    with TestStep("LLM returns set_properties tool calls", assistant=assistant):
        m = assistant.chat_session.messages[1]
        assert assistant.tool_calls is not None
        assert len(assistant.tool_calls) == 1
        assert assistant.tool_calls[0].name == "set_properties"
        assert "plot_overview" in assistant.tool_calls[0].arguments["properties"]
        assert len(assistant.tool_calls[0].arguments["properties"]["plot_overview"]) > 10
        assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS

    with TestStep("set_properties tool result", assistant=assistant):
        m = assistant.chat_session.messages[-1]
        assert m.role == "tool"
        assert "Set `plot_overview`" in m.content
        assert assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS


    with TestStep("Call LLM With Tool Output that set_properties tool returns", assistant=assistant):
        # assert len(assistant.chat_session.messages) == 10
        m = assistant.chat_session.messages[-1]
        assert m.role == "assistant"
        assert len(assistant.tool_calls) == 0
        assert "plot" in m.content.lower()
        assert "overview" in m.content.lower()
        assert assistant.state == AssistantState.WAITING_USER_INPUT
        assert assistant.story.genre.lower() == "science fiction"
        # Add checks for plot_overview
        assert assistant.story.plot_overview is not None
        assert len(assistant.story.plot_overview) > 50

    # Round 4

    with TestStep("User requests to add a character", assistant=assistant):
        assistant.send_message("Add a character")
        # assert len(assistant.chat_session.messages) == 11
        m = assistant.chat_session.messages[-1]
        assert m.role == "user"
        assert assistant.state == AssistantState.GENERATING_OUTPUT

    # Tool calls to set the story overview and other properties
    with TestStep("LLM returns creative_write tool calls for character", assistant=assistant):
        # assert len(assistant.chat_session.messages) == 11
        m = assistant.chat_session.messages[-1]
        assert assistant.tool_calls is not None
        assert len(assistant.tool_calls) == 1
        assert assistant.tool_calls[0].name == "creative_write"
        assert "character" in assistant.tool_calls[0].arguments["prompt"].lower()
        assert "create" in assistant.tool_calls[0].arguments["prompt"].lower()
        assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS

    with TestStep("creative_write tool output for character", assistant=assistant):
        # assert len(assistant.chat_session.messages) == 12
        m = assistant.chat_session.messages[-1]
        assert m.role == "tool"
        assert "Name:" in m.content
        assert len(m.content) > 100
        assert assistant.state == AssistantState.PROCESSING_TOOL_OUTPUTS

    with TestStep("Call LLM With Tool Output that creative_write tool returns for character", assistant=assistant):
        # assert len(assistant.chat_session.messages) == 13
        m = assistant.chat_session.messages[-1]
        assert m.role == "assistant"
        assert m.content == ""  # Content should be empty when there are tool calls
        assert m.show_user is True
        assert len(m.tool_calls) == 1
        assert m.tool_calls[0]["function"]["name"] == "set_properties"
        assert "story_beats" in m.tool_calls[0]["function"]["arguments"]["properties"]
        assert len(m.tool_calls[0]["function"]["arguments"]["properties"]["story_beats"]) > 0
        assert assistant.state == AssistantState.PROCESSING_TOOL_CALLS
        assert assistant.story.genre.lower() == "science fiction"
        # Add checks for plot_overview
        assert assistant.story.plot_overview is not None
        # assert len(assistant.story.plot_overview) > 50

    with TestStep("set story_beats", assistant=assistant):
        """**Updates:**\nSet `story_beats"""
        # assert len(assistant.chat_session.messages) == 12
        m = assistant.chat_session.messages[-1]
        assert m.role == "tool"
        assert "story_beats" in m.content

    with TestStep("LLM responds with character details", assistant=assistant):
        m = assistant.chat_session.messages[-1]
        assert m.role == "assistant"
        assert m.show_user is False
        assert m.tool_calls is None
        
        # Check content structure
        content = m.content
        assert "# New Character Added! 🌟" in content

    with TestStep("inform character added", assistant=assistant):
        """# New Character Added!"""
        # assert len(assistant.chat_session.messages) == 12
        m = assistant.chat_session.messages[-1]
        assert m.role == "assistant"
        assert "New Character Added" in m.content
        assert "Accept all suggestions" in assistant.quick_responses
        assert assistant.state == AssistantState.WAITING_USER_INPUT


