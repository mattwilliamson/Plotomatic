import os
import json
from unidecode import unidecode
import textwrap
from json_repair import repair_json

from typing import List, Optional, Any, Literal
from pydantic import BaseModel, Field, model_validator, PrivateAttr

from IPython.display import display, Markdown


def deindent(text: str) -> str:
    """Remove leading whitespace from each line of text."""
    # return textwrap.dedent(text)
    lines = text.splitlines()
    # Strip leading whitespace from each line
    stripped_lines = [line.lstrip() for line in lines]
    return "\n".join(stripped_lines).strip()


class CharacterRelationship(BaseModel):
    """
    Represents a relationship between two characters in the story.
    """
    character_nickname: Optional[str] = Field("", description='The related character')
    relationship_type: Optional[str] = Field("", description='Type of relationship, e.g., "friend", "enemy", "mentor"')
    description: Optional[str] = Field("", description="Further details about the relationship")


class CharacterArc(BaseModel):
    """
    Represents the development arc of a character over the course of the story.
    """
    initial_state: Optional[str] = Field("", description='The character\'s initial state at the beginning of the story')
    final_state: Optional[str] = Field("", description='The character\'s final state at the end of the story')
    key_moments: Optional[List[str]] = Field(default_factory=list, description="Key moments that define this arc")


class Character(BaseModel):
    """
    Represents a character in the story, including their attributes, relationships, and development.
    """
    nickname: Optional[str] = Field("", description="Unique nickname used as an identifier for the character")
    name: Optional[str] = Field("", description="Full name of the character")
    description: Optional[str] = Field("", description="Description of the character")
    personality: Optional[str] = Field("", description="Personality traits of the character")
    physical_appearance: Optional[str] = Field("", description="Physical appearance of the character")
    role: Optional[str] = Field("", description="Role of the character in the story")
    gender: Optional[str] = Field("", description="Gender of the character")
    race: Optional[str] = Field("", description="Race or species of the character, e.g., human, elf, android, cat")
    age: Optional[str] = Field("", description="Age of the character")
    catch_phrase: Optional[str] = Field("", description="Catchphrase of the character")
    animation_description: Optional[str] = Field("", description="Description of character animation")
    voice_description: Optional[str] = Field("", description="Description of character's voice")
    props: Optional[List[str]] = Field(default_factory=list, description="List of props associated with the character")
    relationships: Optional[List[CharacterRelationship]] = Field(default_factory=list, description="Relationships with other characters")
    internal_conflict: Optional[str] = Field("", description="Internal conflict or struggle of the character")
    character_arc: Optional[CharacterArc] = Field(None, description="Character development arc")
    image_prompt: Optional[str] = Field("", description="Prompt for generating an image of the character")
    image_prompt_short: Optional[str] = Field("", description="Short prompt for generating an image of the character")

    def markdown_summary(self) -> str:
        """Generates a Markdown summary for a single character, including role, description, and internal conflict."""
        markdown = deindent(f"""
            ## Character: "{self.name}"
            **Character Nickname**: "{self.nickname}"
            **Role**: {self.role}
            **Description**: {self.description}
            **Personality**: {self.personality}
            **Appearance**: {self.physical_appearance}
            **Internal Conflict**: {self.internal_conflict or 'none'}
        """)

        if self.character_arc:
            markdown += deindent(f"""
                #### Character Arc:
                - Initial State: {self.character_arc.initial_state}
                - Final State: {self.character_arc.final_state}
                - Key Moments: {', '.join(self.character_arc.key_moments)}
            """)
        return markdown



class Prop(BaseModel):
    """
    Represents a prop in the story, including its description and purpose.
    """
    name: Optional[str] = Field("", description="Name of the prop")
    description: Optional[str] = Field("", description="Description of the prop")
    purpose: Optional[str] = Field("", description="Purpose of the prop in the story")
    physical_appearance: Optional[str] = Field("", description="Physical appearance of the prop")
    animation_description: Optional[str] = Field("", description="Description of prop animation")


class DialogueLine(BaseModel):
    """
    Represents a line of dialogue spoken by a character in a scene.
    """
    character_nickname: Optional[str] = Field("", description='Nickname of the character speaking the line')
    line: Optional[str] = Field("", description='The line of dialogue')


class Scene(BaseModel):
    """
    Represents a scene in the story, including setting, characters, and dialogue.
    """
    scene_id: Optional[str] = Field("", description="Unique identifier for the scene")
    title: Optional[str] = Field("", description="Title of the scene")
    description: Optional[str] = Field("", description="Description of the scene")
    characters_involved_nicknames: Optional[List[str]] = Field(default_factory=list, description="List of character nicknames involved in the scene")
    setting: Optional[str] = Field("", description="Setting of the scene")
    time_of_day: Optional[str] = Field("", description="Time of day when the scene takes place")
    location: Optional[str] = Field("", description="Location of the scene")
    lighting: Optional[str] = Field("", description="Lighting description for the scene")
    mood: Optional[str] = Field("", description="Mood of the scene")
    props: Optional[List[str]] = Field(default_factory=list, description="List of props used in the scene")
    key_actions: Optional[List[str]] = Field(default_factory=list, description="Key actions that take place in the scene")
    # dialogue: Optional[List[DialogueLine]] = Field(default_factory=list, description="List of dialogue lines in the scene")
    background_image_prompt: Optional[str] = Field("", description="Prompt for generating an image of the character")
    background_animation: Optional[str] = Field("", description="Description of scene animation of background")
    scene_image_prompt: Optional[str] = Field("", description="Prompt for generating an image of the scene")
    scene_image_prompt_short: Optional[str] = Field("", description="Short prompt for generating an image of the scene")

    def markdown_summary(self) -> str:
        """Generates a Markdown summary for a single scene, including setting, characters involved, and key actions."""
        markdown = deindent(f"""
            ##### Scene: "{self.title}"
            **Scene ID**: {self.scene_id}
            **Setting**: {self.setting}
            **Time of Day**: {self.time_of_day}
            **Location**: {self.location}
            **Lighting**: {self.lighting}
            **Mood**: {self.mood}
            **Characters Involved (by nickname)**: {', '.join(self.characters_involved_nicknames)}
            **Props**: {', '.join(self.props)}
        """)

        if self.key_actions:
            markdown += "\n###### Key Actions:\n"
            for action in self.key_actions:
                markdown += f"- {action}\n"
            markdown += "\n"

        markdown += deindent(f"""
            ###### Description:
            {self.description}
        """)

        return markdown



class Chapter(BaseModel):
    """
    Represents a chapter within an act, containing multiple scenes.
    """
    chapter_id: Optional[str] = Field("", description="Unique identifier for the chapter")
    title: Optional[str] = Field("", description="Title of the chapter")
    description: Optional[str] = Field("", description="Description of the chapter")
    scenes: Optional[List[Scene]] = Field(default_factory=list, description="List of scenes in this chapter")

    def markdown_summary(self, include_scenes: bool = True) -> str:
        """Generates a Markdown summary for a chapter, optionally including details on each scene."""
        markdown = f'#### Chapter: "{self.title}"\n\n'
        markdown += f"**Chapter ID**: {self.chapter_id}\n"
        markdown += f"Description:\n{self.description}\n\n"

        if include_scenes:
            for scene in self.scenes:
                markdown += scene.markdown_summary()
        return markdown


class StoryBeat(BaseModel):
    """
    Represents a significant moment or turning point in the story.
    """
    name: Optional[str] = Field("", description='Name of the story beat, e.g., "Inciting Incident", "Climax"')
    description: Optional[str] = Field("", description='Explanation of the beat\'s importance in the story')
    scene: Optional[str] = Field("", description="Link to a scene if applicable")


class Subplot(BaseModel):
    """
    Represents a subplot that runs alongside the main plot of the story.
    """
    title: Optional[str] = Field("", description='Title of the subplot')
    description: Optional[str] = Field("", description="Description of the subplot")
    related_characters: Optional[List[str]] = Field(default_factory=list, description="Characters involved in this subplot")


class EmotionalArc(BaseModel):
    """
    Represents an emotional stage or shift within the story.
    """
    stage: Optional[str] = Field("", description='The emotional stage, e.g., "Hopeful", "Despair", "Triumphant"')
    description: Optional[str] = Field("", description="Further explanation of this emotional stage")


class Act(BaseModel):
    """
    Represents an act within the story, containing multiple chapters and props.
    """
    act_id: Optional[str] = Field("", description="Unique identifier for the act")
    title: Optional[str] = Field("", description="Title of the act")
    description: Optional[str] = Field("", description="Description of the act")
    chapters: Optional[List[Chapter]] = Field(default_factory=list, description="List of chapters in this act")
    props: Optional[List[str]] = Field(default_factory=list, description="List of prop names used in this act")

    def markdown_summary(self, include_chapters: bool = True, include_scenes: bool = True) -> str:
        """Generates a Markdown summary for an act, optionally including details on chapters and scenes."""
        markdown = deindent(f"""
            ### Act: "{self.title}"
            **Act ID**: {self.act_id}
            Description:
            {self.description}
        """)

        if include_chapters:
            for chapter in self.chapters:
                markdown += "\n"
                markdown += chapter.markdown_summary(include_scenes=include_scenes)
        return markdown


class SceneDialogue(BaseModel):
    """
    Represents the dialogues for a specific scene.
    Dialogues are organized by character and line and would be used for movies and such.
    """
    scene_id: Optional[str] = Field("", description="Unique identifier of the scene this dialogue belongs to")
    dialogues: Optional[List[DialogueLine]] = Field(default_factory=list, description="List of dialogue lines in the scene for screenplays")
    content: Optional[str] = Field("", description="Content of the scene")


class ChapterDialogue(BaseModel):
    """
    Represents dialogues for a chapter, containing dialogues for multiple scenes.
    """
    chapter_id: Optional[str] = Field("", description="Unique identifier of the chapter this dialogue belongs to")
    scene_dialogues: List[SceneDialogue] = Field(default_factory=list, description="List of SceneDialog objects for the chapter")



class ActDialogue(BaseModel):
    """
    Represents dialogues for an act, containing dialogues for multiple chapters.
    """
    act_id: Optional[str] = Field("", description="Unique identifier of the act this dialogue belongs to")
    chapter_dialogues: List[ChapterDialogue] = Field(default_factory=list, description="List of ChapterDialog objects for the act")


class StoryDialogue(BaseModel):
    """
    Represents the dialogues for the entire story, organized by acts and scenes.
    """
    act_dialogues: List[ActDialogue] = Field(default_factory=list, description="List of ActDialog objects for the story")

    # Private attribute to hold the reference back to the Story
    _story: Optional['Story'] = PrivateAttr(default=None)

    def set_story(self, story: 'Story'):
        """
        Set the associated Story and establish a reverse reference.
        """
        self._story = story
        story._story_dialog = self  # Set reverse reference

    def get_story(self) -> Optional['Story']:
        """
        Get the associated Story.
        """
        return self._story
    
    @property
    def valid_scene_ids(self) -> List[str]:
        """Get a list of valid scene IDs from the associated Story."""
        if self._story is None:
            return []
        return [scene.scene_id for act in self._story.acts for scene in act.scenes]

    @property
    def valid_character_nicknames(self) -> List[str]:
        """Get a list of valid character nicknames from the associated Story."""
        if self._story is None:
            return []
        return self._story.valid_character_nicknames

    @model_validator(mode='after')
    def check_references(self) -> 'StoryDialogue':
        """Check that the scene IDs and character nicknames in the dialogues are valid."""
        valid_scene_ids = self.valid_scene_ids
        valid_character_nicknames = self.valid_character_nicknames

        if not valid_character_nicknames:
            return self

        for act_dialog in self.act_dialogues:
            for scene_dialog in act_dialog.scene_dialogues:
                if scene_dialog.scene_id not in valid_scene_ids:
                    raise ValueError(f"Invalid scene_id: {scene_dialog.scene_id}")
                for dialogue in scene_dialog.dialogues:
                    if dialogue.character_nickname and dialogue.character_nickname.lower() not in valid_character_nicknames:
                        print(f"Invalid character_nickname: {dialogue.character_nickname}({valid_character_nicknames})")
                        raise ValueError(f"Invalid character_nickname: {dialogue.character_nickname}")
        return self


class Story(BaseModel):
    """
    Represents the overall story, including its structure, characters, plot, and acts.
    """
    author: Optional[str] = Field("", description="Author of the story")
    prompt: Optional[str] = Field("", description="Prompt or inspiration for the story")
    title: Optional[str] = Field("", description="Title of the story")
    has_video: Optional[bool] = Field(False, description="Whether the story is animated")
    has_images: Optional[bool] = Field(False, description="Whether the story includes images")
    visual_style: Optional[str] = Field("", description="Visual style of the story, e.g., 'Anime', 'Realistic'")
    title_image_prompt: Optional[str] = Field("", description="Prompt for generating an image of the title")
    cover_image_prompt: Optional[str] = Field("", description="Prompt for generating a cover image")
    tagline: Optional[str] = Field("", description="Tagline for the story")
    time_period: Optional[str] = Field("", description="Time period in which the story is set")
    location: Optional[str] = Field("", description="Location where the story takes place")
    genre: Optional[str] = Field("", description="Genre of the story, e.g., 'Fantasy', 'Sci-fi'")
    medium: Optional[str] = Field("", description="Medium of the story, e.g., 'Book', 'Film'")
    plot_overview: Optional[str] = Field("", description="Overview of the plot")
    narrative_perspective: Optional[str] = Field("", description="Narrative perspective, e.g., 'First-person', 'Third-person'")
    conflict_type: Optional[str] = Field("", description="Type of conflict in the story, e.g., 'person vs person', 'person vs nature'")
    themes: Optional[List[str]] = Field(default_factory=list, description="Central themes in the story")
    motifs: Optional[List[str]] = Field(default_factory=list, description="Recurring motifs or symbols in the story")
    characters: Optional[List[Character]] = Field(default_factory=list, description="List of characters in the story")
    props: Optional[List[Prop]] = Field(default_factory=list, description="List of props in the story")
    story_beats: Optional[List[StoryBeat]] = Field(default_factory=list, description="List of key narrative beats in the story")
    subplots: Optional[List[Subplot]] = Field(default_factory=list, description="Subplots running alongside the main plot")
    emotional_arc: Optional[List[EmotionalArc]] = Field(default_factory=list, description="Track the emotional shifts in the story")
    acts: Optional[List[Act]] = Field(default_factory=list, description="Acts or chapters to organize the story structure")
    act_count: Optional[str] = Field("3", description="Number of acts in the story")
    avg_chapter_count: Optional[str] = Field("", description="Average number of scenes per act")
    avg_chapter_length: Optional[str] = Field("", description="Average length of scenes in words")
    avg_chapters_per_act: Optional[str] = Field("", description="Average number of chapters per act")

    # Private attribute to hold the reference to the associated StoryDialog
    _story_dialog: Optional['StoryDialogue'] = PrivateAttr(default=None)

    def set_story_dialogue(self, story_dialog: 'StoryDialogue'):
        """
        Set the associated StoryDialog and establish a reverse reference.
        """
        self._story_dialog = story_dialog
        story_dialog._story = self  # Set reverse reference

    def get_story_dialogue(self) -> Optional['StoryDialogue']:
        """
        Get the associated StoryDialog.
        """
        return self._story_dialog

    @property
    def valid_character_nicknames(self) -> List[str]:
        """Get a list of valid character nicknames from the associated Story."""
        return [char.nickname or char.name.lower() for char in self.characters]

    def markdown_overview(self) -> str:
        """Generates a Markdown overview for the story, including title, genre, setting, themes, and other high-level details."""

        markdown = deindent(f"""
            # Story: {self.title}

            **Medium**: {self.medium}
            **Genre**: {self.genre}
            **Visual** Style: {self.visual_style}
            **Time Period**: {self.time_period}
            **Location**: {self.location}
            **Narrative Perspective**: {self.narrative_perspective}
            **Conflict Type**: {self.conflict_type}
            **Themes**: {', '.join(self.themes) if self.themes else 'None'}
            **Motifs**: {', '.join(self.motifs) if self.motifs else 'None'}

            ## Original User Prompt:
            {self.prompt}

            ## Plot Overview:
            {self.plot_overview}
        """)

        # Story Beats
        if self.story_beats:
            markdown += "\n\n## Story Beats\n\n"
            for beat in self.story_beats:
                if beat.scene:
                    markdown += f"- {beat.name}: {beat.description} (Scene: {beat.scene})\n"
                else:
                    markdown += f"- {beat.name}: {beat.description}\n"

        # Subplots
        if self.subplots:
            markdown += "## Subplots\n\n"
            for subplot in self.subplots:
                markdown += deindent(f"""
                    ### Subplot: "{subplot.title}"

                    **Related Characters (nicknames)**: {', '.join(subplot.related_characters)}

                    #### Description:
                    {subplot.description}
                """ + "\n\n")

        # Emotional Arc
        if self.emotional_arc:
            markdown += "\n## Emotional Arcs\n\n"
            for arc in self.emotional_arc:
                markdown += f"- {arc.stage}: {arc.description}\n"

        return markdown
    
    def markdown_full_summary(self, include_characters: bool = True, include_acts: bool = True, include_chapters: bool = True, include_scenes: bool = True) -> str:
        """Generates a full Markdown summary for the entire story, including overview, characters, acts, chapters, and scenes."""
        markdown = self.markdown_overview()
        
        # Characters
        if include_characters:
            markdown += "\n\n### Characters\n\n"
            for character in self.characters:
                markdown += character.markdown_summary() + "\n\n"
        
        # Acts, Chapters, and Scenes
        if include_acts:
            markdown += "\n\n## Acts, Chapters, and Scenes\n\n"
            for act in self.acts:
                markdown += act.markdown_summary(include_chapters=include_chapters, include_scenes=include_scenes) + "\n"

        return markdown




    # @model_validator(mode='after')
    # def check_references(self) -> 'Story':
    #     """Check that the character nicknames in the scene are valid."""
    #     valid_character_nicknames = self.valid_character_nicknames

    #     if not valid_character_nicknames:
    #         return self

    #     for act in self.acts:
    #         for scene in act.scenes:
    #             for character_involved in scene.characters_involved_nicknames:
    #                 if character_involved.lower() not in valid_character_nicknames:
    #                     raise ValueError(f"Invalid character_nickname: {character_involved} in scene {scene.scene_id}")
    #     return self

    @classmethod
    def model_validate_json(cls, json_data: str | bytes | bytearray, *, strict: bool | None = None, context: Any | None = None) -> "Story":
        """Parse JSON into a Story instance. We override it to remove smart quotes, em-dashes, and other non-ASCII characters."""
        json_data = unidecode(json_data)
        json_data = repair_json(json_data)
        return super().model_validate_json(json_data, strict=strict, context=context)
    
    # def model_dump_json(
    #     self,
    #     *,
    #     indent: int | None = None,
    #     include: any = {},
    #     exclude: any = {},
    #     **kwargs
    # ) -> str:
    #     js = super().model_dump_json(
    #         indent=indent,
    #         include=include,
    #         exclude=exclude,
    #         **kwargs
    #     )
    #     return unidecode(js)

    # def short_context(self) -> str:
    #     """Return a short context string for the story to pass into LLMs as context"""
    #     data_dict = self.model_dump(include=["prompt", "title", "genre", "medium", "visual_style", "location", "time_period", "plot_overview"])
    #     return json.dumps(data_dict, indent=4)
    #     # return json.dumps(data_dict)
    
    # def classification_context(self) -> str:
    #     """Return a JSON string with the classification fields of the story"""
    #     data_dict = self.model_dump(include=["genre", "medium", "visual_style", "location", "time_period"])
    #     return json.dumps(data_dict, indent=4)
    #     # return json.dumps(data_dict)
    
    # def full_context(self) -> str:
    #     """Return a JSON string with the classification fields of the story"""
    #     data_dict = self.model_dump()
    #     return json.dumps(data_dict, indent=4)
    #     # return json.dumps(data_dict)

    # def prop_context(self) -> str:
    #     """Return a JSON string without the props"""
    #     story = self.copy()
    #     story.props = []
    #     for scene in story.scenes:
    #         scene.props = []
    #     for character in story.characters:
    #         character.props = []
    #     return story.model_dump_json(indent=4)

    def display(self):
        """Pretty print JSON of the story in python notebook"""
        # json_pretty = self.model_dump_json(indent=4, exclude_none=True, exclude_defaults=True)
        json_pretty = self.model_dump_json(indent=4)
        display(Markdown(f"### Story Details\n\n```json\n{json_pretty}\n```"))

    def copy(self) -> "Story":
        """Return a deep copy of the current story instance."""
        return self.model_copy(deep=True)
    
    def save_to_directory(self, directory_path: str):
        """Save the story and its associated story_dialog to a directory as JSON files."""
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

        # Save the story data as JSON
        story_data = self.model_dump_json(indent=4)
        story_data = unidecode(story_data)
        json_path = os.path.join(directory_path, "story.json")
        with open(json_path, "w") as json_file:
            json_file.write(story_data)

        # Save the story_dialog if it exists
        if self._story_dialog is not None:
            # Save the StoryDialog data as JSON
            story_dialog_data = self._story_dialog.model_dump_json(indent=4)
            story_dialog_data = unidecode(story_dialog_data)
            story_dialog_json_path = os.path.join(directory_path, "story_dialog.json")
            with open(story_dialog_json_path, "w") as json_file:
                json_file.write(story_dialog_data)

    @classmethod
    def load_from_directory(cls, directory_path: str) -> 'Story':
        """Load a story and its associated story_dialog from a directory containing JSON files."""
        # Load the story data from JSON
        json_path = os.path.join(directory_path, "story.json")
        with open(json_path, "r") as json_file:
            story_data = json.load(json_file)

        # Create the story object
        story = cls(**story_data)

        # Attempt to load the story_dialog
        try:
            story_dialog = story.load_story_dialog(directory_path)
            # Establish references
            story.set_story_dialogue(story_dialog)
        except FileNotFoundError:
            story_dialog = None  # No story_dialog found

        return story
    
    def load_story_dialog(self, directory_path: str) -> StoryDialogue:
        """Load the associated StoryDialog from a directory containing a story_dialog.json file."""
        story_dialog_json_path = os.path.join(directory_path, "story_dialog.json")
        with open(story_dialog_json_path, "r") as json_file:
            story_dialog_data = json.load(json_file)
        return StoryDialogue(**story_dialog_data)



example_story = Story(
    prompt="A young wizard embarks on a quest to find a lost artifact.",
    visual_style="Anime",
    genre="Fantasy",
    medium="Book",
    title="The Wizard's Quest",
    location="A magical realm",
    plot_overview="A young wizard embarks on a dangerous quest to recover a lost artifact.",
    time_period="Medieval",
    narrative_perspective="Third-person",
    conflict_type="Person vs. Person",
    motifs=["Magic", "Journey"],
    themes=["Courage", "Redemption"],
    characters=[
        Character(
            nickname="erion",
            name="Erion",
            description="A courageous young wizard.",
            personality="Brave but reckless.",
            physical_appearance="Tall with messy black hair.",
            role="Protagonist",
            gender="Male",
            age="Early 20s",
            catch_phrase="By the power of the elements!",
            relationships=[
                CharacterRelationship(
                    character_nickname="lyria",
                    relationship_type="Friend",
                    description="A close friend and mentor."
                )
            ],
            internal_conflict="Struggles with self-doubt.",
            character_arc=CharacterArc(
                initial_state="Inexperienced and unsure.",
                final_state="Confident and powerful.",
                key_moments=["Defeats the dark sorcerer", "Finds the lost artifact"]
            ),
        ),
        Character(
            nickname="lyria",
            name="Lyria",
            description="A mysterious sorceress.",
            personality="Calm and wise.",
            physical_appearance="Slender with silver hair.",
            role="Mentor",
            gender="Female",
            age="30s",
            catch_phrase="Magic flows through all things.",
            relationships=[
                CharacterRelationship(
                    character_nickname="erion",
                    relationship_type="Mentor",
                    description="Guides Erion on his quest."
                )
            ],
            internal_conflict="Haunted by her past mistakes.",
            character_arc=CharacterArc(
                initial_state="Reserved and secretive.",
                final_state="Open and trusting.",
                key_moments=["Reveals her past", "Helps Erion in the final battle"]
            ),
        )
    ],
    acts=[
        Act(
            act_id="act1",
            title="The Beginning",
            description="The start of Erion's journey.",
            props=["Magic Staff"],
            chapters=[
                Chapter(
                    chapter_id="chapter1",
                    title="Departure",
                    description="Erion leaves his village.",
                    scenes=[
                        Scene(
                            scene_id="scene1",
                            title="The Beginning of the Quest",
                            description="Erion sets out from his village.",
                            characters_involved_nicknames=["erion"],
                            setting="A small village on the edge of a vast forest.",
                            time_of_day="Morning",
                            location="Village",
                            lighting="Bright",
                            mood="Hopeful",
                            props=["Magic Staff"],
                            key_actions=["Erion begins his journey."]
                        )
                    ]
                )
            ]
        )
    ],
    props=[
        Prop(
            name="Magic Staff",
            description="A powerful staff imbued with magical energy.",
            purpose="Helps Erion channel his magic.",
            physical_appearance="A tall wooden staff with glowing runes."
        )
    ],
    subplots=[
        Subplot(
            title="Lyria's Redemption",
            description="Lyria seeks to atone for her past mistakes.",
            related_characters=["lyria"]
        )
    ],
    emotional_arc=[
        EmotionalArc(
            stage="Hopeful",
            description="Erion feels hopeful as he begins his quest."
        )
    ],
    story_beats=[
        StoryBeat(
            name="Inciting Incident",
            description="Erion discovers the lost artifact's location.",
            scene="scene1"
        )
    ]
)

example_story_dialog = StoryDialogue(
    act_dialogues=[
        ActDialogue(
            act_id="act1",
            chapter_dialogues=[
                ChapterDialogue(
                    chapter_id="chapter1",
                    scene_dialogues=[
                        SceneDialogue(
                            scene_id="scene1",
                            dialogues=[
                                DialogueLine(
                                    character_nickname="erion",
                                    line="By the power of the elements, I will find the artifact!"
                                )
                            ]
                        )
                    ]
                )
            ]
        )
    ]
)



if __name__ == "__main__":
    # Test the Story class
    from pprint import pprint

    print("Testing the Story class...")

    # Associate the blank story and story dialog with each other
    example_story.set_story_dialogue(example_story_dialog)

    # Make sure we can marhsal and unmarshal the data
    example_story_json = example_story.model_dump_json()
    example_story_parsed = Story.model_validate_json(example_story_json)
    pprint(example_story_parsed.model_dump())

    print("\n\n--- MARKDOWN ---\n\n")

    print(example_story.markdown_full_summary())



