from typing import List, Optional
from pydantic import Field, PrivateAttr, model_validator

from .base import StoryModel

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
        pass

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
            new_scene_dialogue._chapter_dialogue = self
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
            new_chapter_dialogue._act_dialogue = self
            self.chapter_dialogues.append(new_chapter_dialogue)
        return self.chapter_dialogues[index]

class StoryDialogue(StoryModel):
    """Represents the dialogues for the entire story, organized by acts and scenes."""
    act_dialogues: List[ActDialogue] = Field(default_factory=list, description="List of ActDialogue objects for the story")

    _story: Optional['Story'] = PrivateAttr(default=None)

    def set_story(self, story: 'Story'):
        """Set the associated Story and establish a reverse reference."""
        self._story = story
        story._story_dialogue = self

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
            new_act_dialogue._story_dialogue = self
            self.act_dialogues.append(new_act_dialogue)
        return self.act_dialogues[index]

    @property
    def valid_scene_ids(self) -> List[str]:
        """Get a list of valid scene IDs from the associated Story."""
        if self._story is None:
            return []
        return [scene.scene_id for act in self._story.acts 
                for chapter in act.chapters 
                for scene in chapter.scenes]

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
