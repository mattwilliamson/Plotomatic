import os
import json
from typing import List, Optional, Any
from pydantic import Field, PrivateAttr, field_validator, EmailStr
from IPython.display import display, Markdown
from pathlib import Path

from .base import BaseModel
from .story_dialogue import StoryDialogue, SceneDialogue, ActDialogue, ChapterDialogue
from plotomatic.config.settings import STORY_DIR

def get_step_directory(step_number: int) -> str:
    """Get the directory path for a given step number."""
    step_dir = os.path.join(STORY_DIR, f"step_{step_number}")
    os.makedirs(step_dir, exist_ok=True)
    return step_dir

def deindent(text: str) -> str:
    """Remove leading whitespace from each line of text."""
    lines = text.splitlines()
    stripped_lines = [line.lstrip() for line in lines]
    return "\n".join(stripped_lines).strip()

class CharacterRelationship(BaseModel):
    """Represents a relationship between two characters in the story."""
    character_nickname: Optional[str] = Field(
        "", 
        description="Unique identifier of the related character. Used to link characters together in the story's relationship web"
    )
    relationship_type: Optional[str] = Field(
        "", 
        description='Nature of the connection between characters (e.g., "mentor/student", "siblings", "rivals", "romantic interest"). Defines how characters interact'
    )
    description: Optional[str] = Field(
        "", 
        description="Detailed explanation of the relationship dynamics, history, and how it evolves throughout the story"
    )

class CharacterArc(BaseModel):
    """Represents the development arc of a character over the course of the story."""
    initial_state: Optional[str] = Field(
        "", 
        description="Character's starting emotional, psychological, or situational condition at the beginning of the story. Sets up potential for growth"
    )
    final_state: Optional[str] = Field(
        "", 
        description="Character's transformed state by the story's end. Shows how they've changed through their experiences and choices"
    )
    key_moments: Optional[List[str]] = Field(
        default_factory=list, 
        description="Pivotal scenes or decisions that mark significant steps in the character's development. Tracks their journey of change"
    )

class Character(BaseModel):
    """Represents a character in the story, including their attributes, relationships, and development."""
    nickname: Optional[str] = Field(
        "", 
        description="Unique identifier used to reference this character throughout the story system. Should be short and memorable"
    )
    name: Optional[str] = Field(
        "", 
        description="Character's complete name as it appears in the story. May include titles, middle names, or aliases"
    )
    description: Optional[str] = Field(
        "", 
        description="Comprehensive overview of the character, including their background, motivations, and significance to the story"
    )
    personality: Optional[str] = Field(
        "", 
        description="Key character traits, behavioral patterns, and psychological characteristics that define how the character acts and reacts"
    )
    role: Optional[str] = Field(
        "", 
        description="Character's narrative function in the story (e.g., 'Protagonist', 'Antagonist', 'Mentor', 'Comic Relief'). Guides their plot involvement"
    )
    gender: Optional[str] = Field(
        "", 
        description="Character's gender identity, relevant for pronouns and character dynamics. Can be traditional, non-binary, or unique to the story world"
    )
    race: Optional[str] = Field(
        "", 
        description="Character's ethnic, species, or racial identity. Important for world-building and character representation"
    )
    age: Optional[str] = Field(
        "", 
        description="Character's age or age range. Influences their perspective, capabilities, and relationships with other characters"
    )
    props: Optional[List[str]] = Field(
        default_factory=list, 
        description="Signature items, equipment, or possessions associated with the character. Important for characterization and plot functionality"
    )
    internal_conflict: Optional[str] = Field(
        "", 
        description="Character's primary psychological struggle, inner demons, or personal challenges they must overcome"
    )
    physical_appearance: Optional[str] = Field(
        "", 
        description="Detailed description of the character's visual attributes, including distinctive features, style, and physical characteristics"
    )
    catch_phrase: Optional[str] = Field(
        "", 
        description="Memorable quotes or repeated expressions that are characteristic of this character. Helps establish their unique voice"
    )
    voice_description: Optional[str] = Field(
        "", 
        description="Detailed description of how the character sounds, including accent, speech patterns, vocabulary, and vocal mannerisms"
    )
    image_prompt: Optional[str] = Field(
        "", 
        description="Comprehensive prompt for AI image generation to create a full portrait of the character, including all visual details"
    )
    image_prompt_short: Optional[str] = Field(
        "", 
        description="Condensed version of the image prompt focusing on the most distinctive visual elements for quick character sketches"
    )
    animation_description: Optional[str] = Field(
        "", 
        description="Guidelines for how the character moves, gestures, and expresses themselves in animated sequences. Includes signature poses and movements"
    )
    relationships: Optional[List[CharacterRelationship]] = Field(default_factory=list, description="Relationships with other characters")

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

class Prop(BaseModel):
    """Represents a prop in the story."""
    name: Optional[str] = Field(
        "", 
        description="Unique identifier for the prop. Should be concise but descriptive enough to distinguish it from other props"
    )
    description: Optional[str] = Field(
        "", 
        description="Comprehensive overview of the prop, including its history, significance, and how it affects the story"
    )
    purpose: Optional[str] = Field(
        "", 
        description="Narrative function of the prop, whether practical, symbolic, or both. Explains how it advances plot or reveals character"
    )
    physical_appearance: Optional[str] = Field(
        "", 
        description="Detailed visual description including size, material, condition, and any distinctive features or markings"
    )
    animation_description: Optional[str] = Field(
        "", 
        description="Specific instructions for how the prop moves, behaves, or interacts when animated. Includes special effects or transformations"
    )

class Scene(BaseModel):
    """Represents a scene in the story, including setting, characters, and dialogue."""
    scene_id: Optional[str] = Field(
        "", 
        description="Unique identifier for tracking and referencing this scene within the story structure. Format typically includes act and chapter numbers"
    )
    title: Optional[str] = Field(
        "", 
        description="Descriptive name that captures the scene's main event or purpose. Used for organization and quick reference"
    )
    description: Optional[str] = Field(
        "", 
        description="Detailed overview of what happens in the scene, including key events, character interactions, and their significance to the plot"
    )
    characters_involved_nicknames: Optional[List[str]] = Field(
        default_factory=list, 
        description="List of character identifiers present in the scene. Used to track character appearances and ensure continuity"
    )
    narrative_perspective: Optional[str] = Field(
        "", 
        description="Point of view used in this specific scene. May differ from overall story perspective for dramatic effect"
    )
    setting: Optional[str] = Field(
        "", 
        description="Physical and temporal context where the scene takes place. Includes both location and relevant environmental details"
    )
    time_of_day: Optional[str] = Field(
        "", 
        description="Specific time when the scene occurs. Important for maintaining timeline consistency and setting mood"
    )
    location: Optional[str] = Field(
        "", 
        description="Specific place where the scene unfolds. Should include both broad setting and particular spot within it"
    )
    lighting: Optional[str] = Field(
        "", 
        description="Description of natural or artificial light sources and their effects. Crucial for mood and visual storytelling"
    )
    mood: Optional[str] = Field(
        "", 
        description="Emotional atmosphere and tone of the scene. Guides pacing, dialogue, and character interactions"
    )
    props: Optional[List[str]] = Field(
        default_factory=list, 
        description="Objects that play a role in the scene. Includes both significant story items and environmental details"
    )
    key_actions: Optional[List[str]] = Field(
        default_factory=list, 
        description="Important events, decisions, or movements that occur during the scene. Drives plot forward and affects character development"
    )
    background_image_prompt: Optional[str] = Field(
        "", 
        description="Detailed prompt for AI generation of the scene's setting. Should capture atmosphere, lighting, and key environmental elements"
    )
    background_animation: Optional[str] = Field(
        "", 
        description="Instructions for animating the scene's background elements. Includes environmental motion and atmospheric effects"
    )
    scene_image_prompt: Optional[str] = Field(
        "", 
        description="Comprehensive prompt for generating an image of the scene's key moment, including characters, actions, and setting"
    )
    scene_image_prompt_short: Optional[str] = Field(
        "", 
        description="Condensed version of the scene prompt focusing on the most visually important elements for quick sketches"
    )

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

class Chapter(BaseModel):
    """Represents a chapter within an act, containing multiple scenes."""
    chapter_id: Optional[str] = Field(
        "", 
        description="Unique identifier for the chapter. Used for organization and cross-referencing within the story structure"
    )
    title: Optional[str] = Field(
        "", 
        description="Meaningful name that reflects the chapter's main theme or event. Should intrigue readers while providing context"
    )
    description: Optional[str] = Field(
        "", 
        description="Summary of the chapter's content, including its purpose in the overall narrative and key plot developments"
    )
    scenes: Optional[List[Scene]] = Field(
        default_factory=list, 
        description="Ordered collection of scenes that make up the chapter. Each advances the plot while maintaining narrative flow"
    )

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

class StoryBeat(BaseModel):
    """Represents a significant moment or turning point in the story."""
    name: Optional[str] = Field(
        "", 
        description='Descriptive title for this plot point (e.g., "Inciting Incident", "Midpoint Reversal", "Climactic Battle"). Identifies its role in story structure'
    )
    description: Optional[str] = Field(
        "", 
        description="Detailed explanation of what happens at this point and why it's significant to the overall narrative"
    )
    scene: Optional[str] = Field(
        "", 
        description="Reference to the specific scene where this beat occurs. Helps track dramatic structure across the story"
    )

class Subplot(BaseModel):
    """Represents a subplot that runs alongside the main plot of the story."""
    title: Optional[str] = Field(
        "", 
        description="Distinctive name for this secondary storyline that reflects its theme or central conflict"
    )
    description: Optional[str] = Field(
        "", 
        description="Comprehensive overview of the subplot, including its arc, resolution, and how it enhances the main story"
    )
    related_characters: Optional[List[str]] = Field(
        default_factory=list, 
        description="Characters primarily involved in this subplot. Helps track character engagement across different story threads"
    )

class EmotionalArc(BaseModel):
    """Represents an emotional stage or shift within the story."""
    stage: Optional[str] = Field(
        "", 
        description='Name of the emotional phase (e.g., "Hope", "Despair", "Triumph"). Maps the story\'s emotional journey'
    )
    description: Optional[str] = Field(
        "", 
        description="Detailed explanation of this emotional state, its impact on characters, and how it affects audience engagement"
    )

class Act(BaseModel):
    """Represents an act within the story, containing multiple chapters and props."""
    act_id: Optional[str] = Field(
        "", 
        description="Unique identifier for the act. Used for organization and tracking within the larger story structure"
    )
    title: Optional[str] = Field(
        "", 
        description="Descriptive name that captures the act's main theme or narrative purpose. Often reflects major story phases"
    )
    description: Optional[str] = Field(
        "", 
        description="Comprehensive overview of the act's content, including its role in the overall story arc and major developments"
    )
    purpose: Optional[str] = Field(
        "", 
        description="Act's primary narrative function and how it advances the overall story. Guides pacing and plot development"
    )
    conflicts: Optional[str] = Field(
        "", 
        description="Major tensions and challenges that drive this section of the story. Includes both external and internal conflicts"
    )
    turning_point: Optional[str] = Field(
        "", 
        description="Crucial moment that changes the story's direction. Often represents a major character decision or revelation"
    )
    mood: Optional[str] = Field(
        "", 
        description="Overall emotional tone and atmosphere of the act. Helps maintain consistent pacing and reader engagement"
    )
    transformation: Optional[str] = Field(
        "", 
        description="How characters or situations change during this act. Tracks character development and plot progression"
    )
    key_events: Optional[str] = Field(
        default_factory=list, 
        description="Major plot points and significant moments that occur during this act. Forms the act's dramatic structure"
    )
    chapters: Optional[List[Chapter]] = Field(
        default_factory=list, 
        description="Ordered collection of chapters that comprise this act. Each advances the story while maintaining narrative flow"
    )
    props: Optional[List[str]] = Field(
        default_factory=list, 
        description="Important objects and items featured in this act. Tracks prop usage for continuity and symbolic significance"
    )

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

class CoverDesign(BaseModel):
    """Represents the design elements for the book's cover."""
    cover_image_prompt: Optional[str] = Field(
        "", 
        description="Detailed prompt for AI image generation to create the cover artwork. Should include style, mood, composition, and key visual elements"
    )
    title_image_prompt: Optional[str] = Field(
        "", 
        description="Prompt for generating stylized text or artwork of the book's title. Should specify font style, effects, and integration with cover art"
    )
    background_color: Optional[str] = Field(
        "", 
        description="Primary background color for the cover in hex code or color name. Should complement the cover artwork and maintain readability"
    )
    text_color: Optional[str] = Field(
        "", 
        description="Color for title and author text in hex code or color name. Must provide sufficient contrast with background for optimal readability"
    )
    tagline: Optional[str] = Field(
        "", 
        description="Short, catchy phrase that encapsulates the story's main appeal or unique selling point. Used in marketing and promotion"
    )
    back_cover_tagline: Optional[str] = Field(
        "", 
        description="Short, compelling hook (1-2 sentences) that captures the essence of the story and appears prominently on the back cover"
    )
    back_cover_blurb: Optional[str] = Field(
        "", 
        description="Engaging summary (2-3 paragraphs) that introduces key characters, central conflict, and stakes without revealing major plot twists"
    )

class Story(BaseModel):
    """Represents the overall story, including its structure, characters, plot, and acts."""
    author: Optional[str] = Field(
        "", 
        description="Full name of the story's creator/writer"
    )
    author_email: Optional[str] = Field(
        None, 
        description="Contact email address for the author, used for notifications and communication"
    )
    # prompt: Optional[str] = Field(
    #     "", 
    #     description="Original creative prompt or inspiration that sparked the story idea. Can include themes, concepts, or specific elements to incorporate"
    # )
    genre: Optional[str] = Field(
        "", 
        description="Primary and secondary genre categories that define the story's conventions and reader expectations (e.g., 'Fantasy/Romance', 'Hard Sci-fi')"
    )
    medium: Optional[str] = Field(
        "", 
        description="Primary format or platform for story delivery (e.g., 'Novel', 'Graphic Novel', 'Interactive Fiction', 'Screenplay')"
    )
    plot_overview: Optional[str] = Field(
        "", 
        description="Comprehensive summary of the main storyline, including major plot points, character arcs, and narrative structure. This is the most important field in the story. It must be generated by the user or the creative_write tool."
    )
    title: Optional[str] = Field(
        "", 
        description="Main title of the story. Should be memorable, relevant to the plot, and capture the story's essence"
    )
    narrative_perspective: Optional[str] = Field(
        "", 
        description="Point of view used to tell the story (e.g., 'Multiple first-person', 'First-person present', 'Third-person limited')"
    )
    narrative_style: Optional[str] = Field(
        "", 
        description="Author's distinctive writing approaches, including tone, voice, and stylistic choices. Can be a combination (e.g., 'First-Person, Parallel Narrative', 'Descriptive', 'Stream of consciousness', 'Omniscient, Nonlinear', 'Circular Narrative', 'Epistolary Narrative')"
    )
    time_period: Optional[str] = Field(
        "", 
        description="Historical or fictional era when the story takes place. Influences setting details, technology level, and social context"
    )
    location: Optional[str] = Field(
        "", 
        description="Primary geographical or fictional setting where the story unfolds. Includes specific places, environments, or world-building elements"
    )
    conflict_type: Optional[str] = Field(
        "", 
        description="Primary source of tension driving the story (e.g., 'Person vs. Nature', 'Person vs. Society', 'Person vs. Self')"
    )
    themes: Optional[List[str]] = Field(
        default_factory=list, 
        description="Core ideas, messages, or universal concepts explored throughout the story (e.g., 'Redemption', 'Coming of age', 'Power of friendship')"
    )
    motifs: Optional[List[str]] = Field(
        default_factory=list, 
        description="Recurring symbols, images, or elements that reinforce themes and add depth to the narrative"
    )
    characters: Optional[List[Character]] = Field(
        default_factory=list, 
        description="Collection of all characters that appear in the story, including protagonists, antagonists, and supporting cast. Each character has their own detailed profile"
    )
    props: Optional[List[Prop]] = Field(
        default_factory=list, 
        description="Significant objects, items, or artifacts that play important roles in the story. Includes physical descriptions and narrative purpose"
    )
    story_beats: Optional[List[StoryBeat]] = Field(
        default_factory=list, 
        description="Sequential list of major plot points and turning points that drive the story forward. Maps the story's dramatic structure and pacing"
    )
    subplots: Optional[List[Subplot]] = Field(
        default_factory=list, 
        description="Secondary storylines that weave through the main plot, adding complexity and depth. Often explore supporting characters or parallel themes"
    )
    emotional_arc: Optional[List[EmotionalArc]] = Field(
        default_factory=list, 
        description="Progression of emotional states and tonal shifts throughout the story. Charts how the audience should feel at each stage of the narrative"
    )
    acts: Optional[List[Act]] = Field(
        default_factory=list, 
        description="Major structural divisions of the story, each with its own dramatic purpose, conflict, and resolution. Typically follows traditional act structure (e.g., three-act, five-act)"
    )
    secret_knowledge: Optional[str] = Field(
        "", 
        description="Hidden information, plot twists, or background details known only to the author that influence character decisions and plot development"
    )
    requirements: Optional[List[str]] = Field(
        default_factory=list,
        description="List of user provided requirements that guide the story creation process. Can include writing style, character traits, plot points, etc"
    )
    # visual_style: Optional[str] = Field(
    #     "", 
    #     description="Overall aesthetic approach for visual elements, defining the look and feel of illustrations, animations, or adaptations"
    # )
    cover_design: Optional[CoverDesign] = Field(
        default_factory=CoverDesign, 
        description="Complete visual design specification for the story's cover, including artwork direction, typography, color scheme, and marketing copy"
    )

    _story_dialogue: Optional['StoryDialogue'] = PrivateAttr(default=None)
    
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
        if not self._story_dialogue:
            self._story_dialogue = StoryDialogue()
            self.set_story_dialogue(self._story_dialogue)
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
            
        # Save dialogue data, create it if it doesn't exist
        self.get_story_dialogue()

        if self._story_dialogue:
            dialogue_path = directory_path / "story_dialogue.json"
            with open(dialogue_path, 'w') as f:
                json.dump(self._story_dialogue.model_dump(), f, indent=4)

    # ... markdown_overview, markdown_full_summary, display, copy, save/load methods ...

