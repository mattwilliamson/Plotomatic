import os
import json
from typing import List, Optional, Any
from pydantic import Field, PrivateAttr, field_validator, EmailStr
from IPython.display import display, Markdown
from pathlib import Path

from .base import StoryModel
from .dialog import StoryDialogue
import settings

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
    race: Optional[str] = Field("", description="Race or species of the character")
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
        pass

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
            new_scene._chapter = self
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
            new_chapter._act = self
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
    author_email: Optional[EmailStr] = Field(None, description="Author's email address")
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

    _story_dialogue: Optional['StoryDialogue'] = PrivateAttr(default=None)

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

    def set_story_dialogue(self, story_dialogue: 'StoryDialogue'):
        """Set the associated StoryDialogue and establish a reverse reference."""
        self._story_dialogue = story_dialogue
        story_dialogue._story = self

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
            new_act._story = self
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
        """Get a list of valid character nicknames."""
        return [char.nickname or char.name.lower() for char in self.characters]

    @classmethod
    def load_from_directory(cls, directory_path: Path) -> Optional['Story']:
        """
        Load a Story instance from a directory containing story.json and story_dialogue.json.
        
        Args:
            directory_path: Path to the directory containing the story files
            
        Returns:
            Story instance if files exist and are valid, None otherwise
        """
        story_path = directory_path / "story.json"
        dialogue_path = directory_path / "story_dialogue.json"
        
        if not story_path.exists():
            return None
            
        # Load main story data
        with open(story_path, 'r') as f:
            story_data = json.load(f)
            
        story = cls(**story_data)
        
        # Load dialogue if it exists
        if dialogue_path.exists():
            with open(dialogue_path, 'r') as f:
                dialogue_data = json.load(f)
                story_dialogue = StoryDialogue(**dialogue_data)
                story.set_story_dialogue(story_dialogue)
        
        # Set parent references for nested objects
        story.set_parent_references()
        
        return story

    def save_to_directory(self, directory_path: Path):
        """
        Save the Story instance to a directory as story.json and story_dialogue.json.
        
        Args:
            directory_path: Path to the directory where files should be saved
        """
        directory_path.mkdir(parents=True, exist_ok=True)
        
        # Save main story data
        story_path = directory_path / "story.json"
        with open(story_path, 'w') as f:
            json.dump(self.model_dump(), f, indent=4)
            
        # Save dialogue data if it exists
        if self._story_dialogue:
            dialogue_path = directory_path / "story_dialogue.json"
            with open(dialogue_path, 'w') as f:
                json.dump(self._story_dialogue.model_dump(), f, indent=4)

    # ... markdown_overview, markdown_full_summary, display, copy, save/load methods ...
