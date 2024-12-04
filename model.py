import os
import json
from unidecode import unidecode
import textwrap
from json_repair import repair_json
import settings

from typing import List, Optional, Any
from pydantic import BaseModel, Field, model_validator, PrivateAttr, field_validator


from IPython.display import display, Markdown

class StoryModel(BaseModel):
    @classmethod
    def model_validate_json(cls, json_data: str | bytes | bytearray, *, strict: bool | None = None, context: Any | None = None) -> "StoryModel":
        """Parse JSON into a StoryModel instance, removing non-ASCII characters."""
        json_data = json_data.strip()
        json_data = unidecode(json_data)
        json_data = repair_json(json_data)
        return super().model_validate_json(json_data, strict=strict, context=context)

def get_step_directory(step_number: int) -> str:
    """Get the directory path for a given step number."""
    step_dir = os.path.join(settings.STORY_DIR, f"step_{step_number}")
    os.makedirs(step_dir, exist_ok=True)
    return step_dir

def deindent(text: str) -> str:
    """Remove leading whitespace from each line of text."""
    lines = text.splitlines()
    stripped_lines = [line.lstrip() for line in lines]
    return "\n".join(stripped_lines).strip()

class CharacterRelationship(StoryModel):
    """Represents a relationship between two characters in the story."""
    character_nickname: Optional[str] = Field("", description='The related character')
    relationship_type: Optional[str] = Field("", description='Type of relationship, e.g., "friend", "enemy", "mentor"')
    description: Optional[str] = Field("", description="Further details about the relationship")

class CharacterArc(StoryModel):
    """Represents the development arc of a character over the course of the story."""
    initial_state: Optional[str] = Field("", description='The character\'s initial state at the beginning of the story')
    final_state: Optional[str] = Field("", description='The character\'s final state at the end of the story')
    key_moments: Optional[List[str]] = Field(default_factory=list, description="Key moments that define this arc")

class Character(StoryModel):
    """Represents a character in the story, including their attributes, relationships, and development."""
    nickname: Optional[str] = Field("", description="Unique nickname used as an identifier for the character")
    name: Optional[str] = Field("", description="Full name of the character")
    description: Optional[str] = Field("", description="Description of the character")
    personality: Optional[str] = Field("", description="Personality traits of the character")
    role: Optional[str] = Field("", description="Role of the character in the story")
    gender: Optional[str] = Field("", description="Gender of the character")
    race: Optional[str] = Field("", description="Race or species of the character, e.g., human, elf, android, cat")
    age: Optional[str] = Field("", description="Age of the character")
    props: Optional[List[str]] = Field(default_factory=list, description="List of props associated with the character")
    internal_conflict: Optional[str] = Field("", description="Internal conflict or struggle of the character")
    character_arc: Optional[CharacterArc] = Field(None, description="Character development arc")
    physical_appearance: Optional[str] = Field("", description="Physical appearance of the character")
    catch_phrase: Optional[str] = Field("", description="Catchphrase of the character")
    voice_description: Optional[str] = Field("", description="Description of character's voice")
    relationships: Optional[List[CharacterRelationship]] = Field(default_factory=list, description="Relationships with other characters")
    image_prompt: Optional[str] = Field("", description="Prompt for generating an image of the character")
    image_prompt_short: Optional[str] = Field("", description="Short prompt for generating an image of the character")
    animation_description: Optional[str] = Field("", description="Description of character animation")

    @field_validator('age', mode='before')
    @classmethod
    def age_to_string(cls, value):
        return str(value)

    def markdown_summary(self) -> str:
        """Generates a Markdown summary for a single character."""
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

class Prop(StoryModel):
    """Represents a prop in the story."""
    name: Optional[str] = Field("", description="Name of the prop")
    description: Optional[str] = Field("", description="Description of the prop")
    purpose: Optional[str] = Field("", description="Purpose of the prop in the story")
    physical_appearance: Optional[str] = Field("", description="Physical appearance of the prop")
    animation_description: Optional[str] = Field("", description="Description of prop animation")

class Scene(StoryModel):
    """Represents a scene in the story, including setting, characters, and dialogue."""
    scene_id: Optional[str] = Field("", description="Unique identifier for the scene")
    title: Optional[str] = Field("", description="Title of the scene")
    description: Optional[str] = Field("", description="Description of the scene")
    characters_involved_nicknames: Optional[List[str]] = Field(default_factory=list, description="List of character nicknames involved in the scene")
    narrative_perspective: Optional[str] = Field("", description="Narrative perspective of the scene")
    setting: Optional[str] = Field("", description="Setting of the scene")
    time_of_day: Optional[str] = Field("", description="Time of day when the scene takes place")
    location: Optional[str] = Field("", description="Location of the scene")
    lighting: Optional[str] = Field("", description="Lighting description for the scene")
    mood: Optional[str] = Field("", description="Mood of the scene")
    props: Optional[List[str]] = Field(default_factory=list, description="List of props used in the scene")
    key_actions: Optional[List[str]] = Field(default_factory=list, description="Key actions that take place in the scene")
    background_image_prompt: Optional[str] = Field("", description="Prompt for generating an image of the character")
    background_animation: Optional[str] = Field("", description="Description of scene animation of background")
    scene_image_prompt: Optional[str] = Field("", description="Prompt for generating an image of the scene")
    scene_image_prompt_short: Optional[str] = Field("", description="Short prompt for generating an image of the scene")

    _chapter: Optional['Chapter'] = PrivateAttr(default=None)

    def set_parent_references(self):
        """Set parent references for nested objects (if any)."""
        pass  # No nested objects to update

    @property
    def _act(self) -> 'Act':
        """Get the parent Act."""
        if not self._chapter or not self._chapter._act:
            raise ValueError("Parent references not set")
        return self._chapter._act

    @property
    def _dialog(self) -> 'SceneDialogue':
        """Get or create the corresponding SceneDialogue instance."""
        if not self._chapter or not self._chapter._act or not self._chapter._act._story:
            raise ValueError("Parent references not set")
        story = self._chapter._act._story
        story_dialogue = story.get_story_dialogue()
        if not story_dialogue:
            story_dialogue = StoryDialogue()
            story.set_story_dialogue(story_dialogue)
        # Find indices
        act_index = story.acts.index(self._chapter._act)
        chapter_index = self._chapter._act.chapters.index(self._chapter)
        scene_index = self._chapter.scenes.index(self)
        # Get or create corresponding dialogue objects
        act_dialogue = story_dialogue.get_or_create_act_dialogue(act_index)
        chapter_dialogue = act_dialogue.get_or_create_chapter_dialogue(chapter_index)
        scene_dialogue = chapter_dialogue.get_or_create_scene_dialogue(scene_index)
        return scene_dialogue

    def markdown_summary(self) -> str:
        """Generates a Markdown summary for a single scene."""
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
            **Description**: {self.description}
            **Narrative Perspective**: {self.narrative_perspective}
            **Key Actions**: {', '.join(self.key_actions) if self.key_actions else 'None'}
            **Characters involved**: {', '.join(self.characters_involved_nicknames)}
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

class Chapter(StoryModel):
    """Represents a chapter within an act, containing multiple scenes."""
    chapter_id: Optional[str] = Field("", description="Unique identifier for the chapter")
    title: Optional[str] = Field("", description="Title of the chapter")
    description: Optional[str] = Field("", description="Description of the chapter")
    scenes: Optional[List[Scene]] = Field(default_factory=list, description="List of scenes in this chapter")

    _act: Optional['Act'] = PrivateAttr(default=None)

    def set_parent_references(self):
        """Set parent references for scenes."""
        for scene in self.scenes:
            scene._chapter = self
            scene.set_parent_references()

    def get_or_create_scene(self, index: int) -> Scene:
        """Get or create a scene by index."""
        while len(self.scenes) <= index:
            new_scene = Scene()
            new_scene._chapter = self  # Set parent reference
            self.scenes.append(new_scene)
        return self.scenes[index]

    @property
    def _dialog(self) -> 'ChapterDialogue':
        """Get or create the corresponding ChapterDialogue instance."""
        if not self._act or not self._act._story:
            raise ValueError("Parent references not set")
        story = self._act._story
        story_dialogue = story.get_story_dialogue()
        if not story_dialogue:
            story_dialogue = StoryDialogue()
            story.set_story_dialogue(story_dialogue)
        # Find indices
        act_index = story.acts.index(self._act)
        chapter_index = self._act.chapters.index(self)
        # Get or create corresponding dialogue objects
        act_dialogue = story_dialogue.get_or_create_act_dialogue(act_index)
        chapter_dialogue = act_dialogue.get_or_create_chapter_dialogue(chapter_index)
        return chapter_dialogue

    def markdown_summary(self, include_scenes: bool = True) -> str:
        """Generates a Markdown summary for a chapter."""
        markdown = f'#### Chapter: "{self.title}"\n\n'
        markdown += f"**Chapter ID**: {self.chapter_id}\n"
        markdown += f"Description:\n{self.description}\n\n"

        if include_scenes:
            for scene in self.scenes:
                markdown += scene.markdown_summary()
        return markdown

class StoryBeat(StoryModel):
    """Represents a significant moment or turning point in the story."""
    name: Optional[str] = Field("", description='Name of the story beat, e.g., "Inciting Incident", "Climax"')
    description: Optional[str] = Field("", description='Explanation of the beat\'s importance in the story')
    scene: Optional[str] = Field("", description="Link to a scene if applicable")

class Subplot(StoryModel):
    """Represents a subplot that runs alongside the main plot of the story."""
    title: Optional[str] = Field("", description='Title of the subplot')
    description: Optional[str] = Field("", description="Description of the subplot")
    related_characters: Optional[List[str]] = Field(default_factory=list, description="Characters involved in this subplot")

class EmotionalArc(StoryModel):
    """Represents an emotional stage or shift within the story."""
    stage: Optional[str] = Field("", description='The emotional stage, e.g., "Hopeful", "Despair", "Triumphant"')
    description: Optional[str] = Field("", description="Further explanation of this emotional stage")

class Act(StoryModel):
    """Represents an act within the story, containing multiple chapters and props."""
    act_id: Optional[str] = Field("", description="Unique identifier for the act")
    title: Optional[str] = Field("", description="Title of the act")
    description: Optional[str] = Field("", description="Description of the act")
    purpose: Optional[str] = Field("", description="Purpose or goal of the act")
    conflicts: Optional[str] = Field("", description="Main conflicts in the act")
    turning_point: Optional[str] = Field("", description="Turning point in the act")
    mood: Optional[str] = Field("", description="Mood of the act")
    transformation: Optional[str] = Field("", description="Transformation or change that occurs in the act")
    key_events: Optional[str] = Field(default_factory=list, description="Key events in the act")
    chapters: Optional[List[Chapter]] = Field(default_factory=list, description="List of chapters in this act")
    props: Optional[List[str]] = Field(default_factory=list, description="List of prop names used in this act")

    @field_validator('key_events', mode='before')
    @classmethod
    def key_events_to_string(cls, value):
        return str(value)

    _story: Optional['Story'] = PrivateAttr(default=None)

    def set_parent_references(self):
        """Set parent references for chapters."""
        for chapter in self.chapters:
            chapter._act = self
            chapter.set_parent_references()

    def get_or_create_chapter(self, index: int) -> Chapter:
        """Get or create a chapter by index."""
        while len(self.chapters) <= index:
            new_chapter = Chapter()
            new_chapter._act = self  # Set parent reference
            self.chapters.append(new_chapter)
        return self.chapters[index]

    @property
    def _dialog(self) -> 'ActDialogue':
        """Get or create the corresponding ActDialogue instance."""
        if not self._story:
            raise ValueError("Parent references not set")
        story_dialogue = self._story.get_story_dialogue()
        if not story_dialogue:
            story_dialogue = StoryDialogue()
            self._story.set_story_dialogue(story_dialogue)
        # Find index
        act_index = self._story.acts.index(self)
        # Get or create corresponding dialogue object
        act_dialogue = story_dialogue.get_or_create_act_dialogue(act_index)
        return act_dialogue

    def markdown_summary(self, include_chapters: bool = True, include_scenes: bool = True) -> str:
        """Generates a Markdown summary for an act."""
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


class Story(StoryModel):
    """Represents the overall story, including its structure, characters, plot, and acts."""
    author: Optional[str] = Field("", description="Author of the story")
    author_email: Optional[str] = Field("", description="Author's email address")
    prompt: Optional[str] = Field("", description="Prompt or inspiration for the story")
    title: Optional[str] = Field("", description="Title of the story")
    has_video: Optional[bool] = Field(False, description="Whether the story is animated")
    has_images: Optional[bool] = Field(False, description="Whether the story includes images")
    narrative_style: Optional[str] = Field("", description="Narrative style of the author")
    cover_image_prompt: Optional[str] = Field("", description="Prompt for generating a cover image")
    title_image_prompt: Optional[str] = Field("", description="Prompt for generating an image of the title")
    cover_background_color: Optional[str] = Field("", description="Background color")
    cover_text_color: Optional[str] = Field("", description="Font color that contrasts with the cover background color")
    back_cover_tagline: Optional[str] = Field("", description="Tagline for the back cover of the book")
    back_cover_blurb: Optional[str] = Field("", description="Blurb for the back cover of the book")
    tagline: Optional[str] = Field("", description="Tagline for the story")
    time_period: Optional[str] = Field("", description="Time period in which the story is set")
    location: Optional[str] = Field("", description="Location where the story takes place")
    genre: Optional[str] = Field("", description="Genre of the story, e.g., 'Fantasy', 'Sci-fi'")
    medium: Optional[str] = Field("", description="Medium of the story, e.g., 'Book', 'Film'")
    plot_overview: Optional[str] = Field("", description="Overview of the plot")
    narrative_perspective: Optional[str] = Field("", description="Narrative perspective, e.g., 'First-person', 'Third-person'")
    conflict_type: Optional[str] = Field("", description="Type of conflict in the story")
    themes: Optional[List[str]] = Field(default_factory=list, description="Central themes in the story")
    motifs: Optional[List[str]] = Field(default_factory=list, description="Recurring motifs or symbols in the story")
    characters: Optional[List[Character]] = Field(default_factory=list, description="List of characters in the story")
    props: Optional[List[Prop]] = Field(default_factory=list, description="List of props in the story")
    story_beats: Optional[List[StoryBeat]] = Field(default_factory=list, description="List of key narrative beats in the story")
    subplots: Optional[List[Subplot]] = Field(default_factory=list, description="Subplots running alongside the main plot")
    emotional_arc: Optional[List[EmotionalArc]] = Field(default_factory=list, description="Track the emotional shifts in the story")
    acts: Optional[List[Act]] = Field(default_factory=list, description="Acts or chapters to organize the story structure")
    act_count: Optional[str] = Field("", description="Number of acts in the story")
    avg_chapter_count: Optional[str] = Field("", description="Average number of scenes per act")
    avg_chapter_length: Optional[str] = Field("", description="Average length of scenes in words")
    avg_chapters_per_act: Optional[str] = Field("", description="Average number of chapters per act")
    secret_knowledge: Optional[str] = Field("", description="Unique details that drive the story behind the scenes")
    visual_style: Optional[str] = Field("", description="Visual style of the story, e.g., 'Anime', 'Realistic'")

    @field_validator('avg_chapters_per_act', mode='before')
    @classmethod
    def avg_chapters_per_act_to_string(cls, value):
        return str(value)
    
    @field_validator('act_count', mode='before')
    @classmethod
    def act_count_to_string(cls, value):
        return str(value)
    
    @field_validator('conflict_type', mode='before')
    @classmethod
    def conflict_type_to_string(cls, value):
        return str(value)
    
    @field_validator('motifs', mode='before')
    @classmethod
    def motifs_to_string(cls, value):
        return [str(value) for value in value]
    

    _story_dialogue: Optional['StoryDialogue'] = PrivateAttr(default=None)

    def set_story_dialogue(self, story_dialogue: 'StoryDialogue'):
        """Set the associated StoryDialogue and establish a reverse reference."""
        self._story_dialogue = story_dialogue
        story_dialogue._story = self  # Set reverse reference

    def get_story_dialogue(self) -> Optional['StoryDialogue']:
        """Get the associated StoryDialogue."""
        return self._story_dialogue

    def set_parent_references(self):
        """Set parent references for acts."""
        for act in self.acts:
            act._story = self
            act.set_parent_references()

    def get_or_create_act(self, index: int) -> Act:
        """Get or create an Act by index."""
        while len(self.acts) <= index:
            new_act = Act()
            new_act._story = self  # Set parent reference
            self.acts.append(new_act)
        return self.acts[index]

    def get_or_create_chapter(self, act_index: int, chapter_index: int) -> Chapter:
        """Get or create a Chapter by act and chapter indices."""
        act = self.get_or_create_act(act_index)
        return act.get_or_create_chapter(chapter_index)

    def get_or_create_scene(self, act_index: int, chapter_index: int, scene_index: int) -> Scene:
        """Get or create a Scene by act, chapter, and scene indices."""
        chapter = self.get_or_create_chapter(act_index, chapter_index)
        return chapter.get_or_create_scene(scene_index)

    @property
    def valid_character_nicknames(self) -> List[str]:
        """Get a list of valid character nicknames from the associated Story."""
        return [char.nickname or char.name.lower() for char in self.characters]

    def markdown_overview(self) -> str:
        """Generates a Markdown overview for the story."""
        markdown = deindent(f"""
            # Story: {self.title}

            **Author**: {self.author}
            **Author Email**: {self.author_email}
            **Medium**: {self.medium}
            **Genre**: {self.genre}
            **Visual Style**: {self.visual_style}
            **Time Period**: {self.time_period}
            **Location**: {self.location}
            **Narrative Perspective**: {self.narrative_perspective}
            **Conflict Type**: {self.conflict_type}
            **Themes**: {', '.join(self.themes) if self.themes else 'None'}
            **Motifs**: {', '.join(self.motifs) if self.motifs else 'None'}
            **Has Video**: {self.has_video}
            **Has Images**: {self.has_images}
            **Title Image Prompt**: {self.title_image_prompt}
            **Cover Image Prompt**: {self.cover_image_prompt}
            **Cover Background Color**: {self.cover_background_color}
            **Cover Text Color**: {self.cover_text_color}
            **Back Cover Blurb**: {self.back_cover_blurb}
            **Tagline**: {self.tagline}
            **Act Count**: {self.act_count}
            **Average Chapter Count**: {self.avg_chapter_count}
            **Average Chapter Length**: {self.avg_chapter_length}
            **Average Chapters per Act**: {self.avg_chapters_per_act}

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
        """Generates a full Markdown summary for the entire story."""
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

    def display(self):
        """Pretty print JSON of the story in a Python notebook."""
        json_pretty = self.model_dump_json(indent=4)
        display(Markdown(f"### Story Details\n\n```json\n{json_pretty}\n```"))

    def copy(self) -> "Story":
        """Return a deep copy of the current story instance."""
        return self.model_copy(deep=True)

    def save_to_directory(self, directory_path: str):
        """Save the story and its associated story_dialogue to a directory as JSON files."""
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

        # Save the story data as JSON
        story_data = self.model_dump_json(indent=4)
        story_data = unidecode(story_data)
        json_path = os.path.join(directory_path, "story.json")
        with open(json_path, "w") as json_file:
            json_file.write(story_data)

        # Save the story_dialogue if it exists
        self._story_dialogue = self._story_dialogue or StoryDialogue()
        if self._story_dialogue is not None:
            story_dialogue_data = self._story_dialogue.model_dump_json(indent=4)
            story_dialogue_data = unidecode(story_dialogue_data)
            story_dialogue_json_path = os.path.join(directory_path, "story_dialogue.json")
            with open(story_dialogue_json_path, "w") as json_file:
                json_file.write(story_dialogue_data)

    @classmethod
    def load_step(cls, step: int) -> 'Story':
        directory_path = get_step_directory(step)
        return cls.load_from_directory(directory_path)

    def save_step(self, step: int):
        """Save the story and its associated story_dialogue to a step directory as JSON files."""
        directory_path = get_step_directory(step)
        self.save_to_directory(directory_path)
        return directory_path

    @classmethod
    def load_from_directory(cls, directory_path: str) -> 'Story':
        """Load a story and its associated story_dialogue from a directory containing JSON files."""
        # Load the story data from JSON
        try:
            json_path = os.path.join(directory_path, "story.json")
            with open(json_path, "r") as json_file:
                story_data = json.load(json_file)
        except FileNotFoundError:
            print(f"Story JSON file not found in directory: {directory_path}")
            story_data = {}

        # Create the story object
        story = cls(**story_data)
        story.set_parent_references()

        # Attempt to load the story_dialogue
        try:
            story_dialogue = story.load_story_dialogue(directory_path)
            # Establish references
            story.set_story_dialogue(story_dialogue)
            story_dialogue.set_parent_references()
        except FileNotFoundError:
            story_dialogue = None  # No story_dialogue found

        return story

    def load_story_dialogue(self, directory_path: str) -> 'StoryDialogue':
        """Load the associated StoryDialogue from a directory containing a story_dialogue.json file."""
        story_dialogue_json_path = os.path.join(directory_path, "story_dialogue.json")
        with open(story_dialogue_json_path, "r") as json_file:
            story_dialogue_data = json.load(json_file)
        story_dialogue = StoryDialogue(**story_dialogue_data)
        story_dialogue.set_parent_references()
        return story_dialogue




class DialogueLine(StoryModel):
    """Represents a line of dialogue spoken by a character in a scene."""
    character_nickname: Optional[str] = Field("", description='Nickname of the character speaking the line')
    line: Optional[str] = Field("", description='The line of dialogue')


class SceneDialogue(StoryModel):
    """Represents the dialogues for a specific scene."""
    scene_id: Optional[str] = Field("", description="Unique identifier of the scene this dialogue belongs to")
    notes: Optional[str] = Field("", description="Notes or comments about the scene")
    dialogues: Optional[List[DialogueLine]] = Field(default_factory=list, description="List of dialogue lines in the scene")
    content: Optional[str] = Field("", description="Content of the scene")

    _chapter_dialogue: Optional['ChapterDialogue'] = PrivateAttr(default=None)

    def set_parent_references(self):
        """Set parent references for nested objects (if any)."""
        pass  # No nested objects to update

    @property
    def _scene(self) -> 'Scene':
        """Get or create the corresponding Scene instance."""
        if not self._chapter_dialogue or not self._chapter_dialogue._act_dialogue or not self._chapter_dialogue._act_dialogue._story_dialogue:
            raise ValueError("Parent references not set")
        story_dialogue = self._chapter_dialogue._act_dialogue._story_dialogue
        story = story_dialogue.get_story()
        if not story:
            raise ValueError("No associated Story found")
        # Find indices
        act_index = story_dialogue.act_dialogues.index(self._chapter_dialogue._act_dialogue)
        chapter_index = self._chapter_dialogue._act_dialogue.chapter_dialogues.index(self._chapter_dialogue)
        scene_index = self._chapter_dialogue.scene_dialogues.index(self)
        # Get or create corresponding story objects
        act = story.get_or_create_act(act_index)
        chapter = act.get_or_create_chapter(chapter_index)
        scene = chapter.get_or_create_scene(scene_index)
        return scene

    @property
    def _act_dialogue(self) -> 'ActDialogue':
        """Get the parent ActDialogue."""
        if not self._chapter_dialogue:
            raise ValueError("Parent chapter dialogue not set")
        return self._chapter_dialogue._act_dialogue

class ChapterDialogue(StoryModel):
    """Represents dialogues for a chapter, containing dialogues for multiple scenes."""
    chapter_id: Optional[str] = Field("", description="Unique identifier of the chapter this dialogue belongs to")
    scene_dialogues: List[SceneDialogue] = Field(default_factory=list, description="List of SceneDialogue objects for the chapter")

    _act_dialogue: Optional['ActDialogue'] = PrivateAttr(default=None)

    def set_parent_references(self):
        """Set parent references for scene dialogues."""
        for scene_dialogue in self.scene_dialogues:
            scene_dialogue._chapter_dialogue = self
            scene_dialogue.set_parent_references()

    def get_or_create_scene_dialogue(self, index: int) -> SceneDialogue:
        """Get or create a SceneDialogue by index."""
        while len(self.scene_dialogues) <= index:
            new_scene_dialogue = SceneDialogue()
            new_scene_dialogue._chapter_dialogue = self  # Set parent reference
            self.scene_dialogues.append(new_scene_dialogue)
        return self.scene_dialogues[index]

class ActDialogue(StoryModel):
    """Represents dialogues for an act, containing dialogues for multiple chapters."""
    act_id: Optional[str] = Field("", description="Unique identifier of the act this dialogue belongs to")
    chapter_dialogues: List[ChapterDialogue] = Field(default_factory=list, description="List of ChapterDialogue objects for the act")

    _story_dialogue: Optional['StoryDialogue'] = PrivateAttr(default=None)

    def set_parent_references(self):
        """Set parent references for chapter dialogues."""
        for chapter_dialogue in self.chapter_dialogues:
            chapter_dialogue._act_dialogue = self
            chapter_dialogue.set_parent_references()

    def get_or_create_chapter_dialogue(self, index: int) -> ChapterDialogue:
        """Get or create a ChapterDialogue by index."""
        while len(self.chapter_dialogues) <= index:
            new_chapter_dialogue = ChapterDialogue()
            new_chapter_dialogue._act_dialogue = self  # Set parent reference
            self.chapter_dialogues.append(new_chapter_dialogue)
        return self.chapter_dialogues[index]


class StoryDialogue(StoryModel):
    """Represents the dialogues for the entire story, organized by acts and scenes."""
    act_dialogues: List[ActDialogue] = Field(default_factory=list, description="List of ActDialogue objects for the story")

    _story: Optional['Story'] = PrivateAttr(default=None)

    def set_story(self, story: 'Story'):
        """Set the associated Story and establish a reverse reference."""
        self._story = story
        story._story_dialogue = self  # Set reverse reference

    def get_story(self) -> Optional['Story']:
        """Get the associated Story."""
        return self._story

    def set_parent_references(self):
        """Set parent references for act dialogues."""
        for act_dialogue in self.act_dialogues:
            act_dialogue._story_dialogue = self
            act_dialogue.set_parent_references()

    def get_or_create_act_dialogue(self, index: int) -> ActDialogue:
        """Get or create an ActDialogue by index."""
        while len(self.act_dialogues) <= index:
            new_act_dialogue = ActDialogue()
            new_act_dialogue._story_dialogue = self  # Set parent reference
            self.act_dialogues.append(new_act_dialogue)
        return self.act_dialogues[index]

    @property
    def valid_scene_ids(self) -> List[str]:
        """Get a list of valid scene IDs from the associated Story."""
        if self._story is None:
            return []
        return [scene.scene_id for act in self._story.acts for chapter in act.chapters for scene in chapter.scenes]

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

        for act_dialogue in self.act_dialogues:
            for chapter_dialogue in act_dialogue.chapter_dialogues:
                for scene_dialogue in chapter_dialogue.scene_dialogues:
                    if scene_dialogue.scene_id not in valid_scene_ids:
                        raise ValueError(f"Invalid scene_id: {scene_dialogue.scene_id}")
                    for dialogue in scene_dialogue.dialogues:
                        if dialogue.character_nickname and dialogue.character_nickname.lower() not in valid_character_nicknames:
                            print(f"Invalid character_nickname: {dialogue.character_nickname}({valid_character_nicknames})")
                            raise ValueError(f"Invalid character_nickname: {dialogue.character_nickname}")
        return self
    

class Message(BaseModel):
    role: str
    content: str

class ChatSession(BaseModel):
    messages: List[Message] = []

    @classmethod
    def load_from_file(cls, path):
        if path.exists():
            import json
            with open(path, 'r') as f:
                data = json.load(f)
            return cls(**data)
        return cls()

    def save_to_file(self, path):
        import json
        with open(path, 'w') as f:
            json.dump(self.dict(), f, indent=4)



# Example usage
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

example_story_dialogue = StoryDialogue(
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

    # Associate the story and story dialogue with each other
    example_story.set_story_dialogue(example_story_dialogue)
    example_story.set_parent_references()
    example_story_dialogue.set_parent_references()

    # Test the convenience functions
    scene = example_story.acts[0].chapters[0].scenes[0]
    scene_dialogue = scene._dialog
    print(f"Scene Dialogue Content: {scene_dialogue.content}")

    # Access the corresponding Scene from SceneDialogue
    scene_from_dialogue = scene_dialogue._scene
    print(f"Scene Title from Dialogue: {scene_from_dialogue.title}")

    # Test accessing parent objects
    act_from_scene = scene._act
    print(f"Act Title from Scene: {act_from_scene.title}")

    # Make sure we can marshal and unmarshal the data
    example_story_json = example_story.model_dump_json()
    example_story_parsed = Story.model_validate_json(example_story_json)
    pprint(example_story_parsed.model_dump())

    print("\n\n--- MARKDOWN ---\n\n")

    print(example_story.markdown_full_summary())


