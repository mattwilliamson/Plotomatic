import os
import json
from unidecode import unidecode
from json_repair import repair_json

from typing import List, Optional, Any, Literal
from pydantic import BaseModel, Field, model_validator, PrivateAttr

from IPython.display import display, Markdown

class CharacterRelationship(BaseModel):
    """
    Represents a relationship between two characters in the story.
    """
    character_name: Optional[str] = Field("", description='The related character')
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
    characters_involved: Optional[List[str]] = Field(default_factory=list, description="List of character nicknames involved in the scene")
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
    Represents an act or chapter within the story, containing multiple scenes and props.
    """
    act_id: Optional[str] = Field("", description="Unique identifier for the act")
    title: Optional[str] = Field("", description="Title of the act or chapter")
    description: Optional[str] = Field("", description="Description of the act")
    scenes: Optional[List[Scene]] = Field(default_factory=list, description="List of scenes in this act")
    props: Optional[List[str]] = Field(default_factory=list, description="List of prop names used in this act")

class SceneDialog(BaseModel):
    """
    Represents the dialogues for a specific scene.
    """
    scene_id: Optional[str] = Field("", description="Unique identifier of the scene this dialogue belongs to")
    dialogues: Optional[List[DialogueLine]] = Field(default_factory=list, description="List of dialogue lines in the scene")

class ActDialog(BaseModel):
    """
    Represents dialogues for an act, containing dialogues for multiple scenes.
    """
    act_id: Optional[str] = Field("", description="Unique identifier of the act this dialogue belongs to")
    scene_dialogs: List[SceneDialog] = Field(default_factory=list, description="List of SceneDialog objects for the act")

class StoryDialog(BaseModel):
    """
    Represents the dialogues for the entire story, organized by acts and scenes.
    """
    act_dialogs: List[ActDialog] = Field(default_factory=list, description="List of ActDialog objects for the story")

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
    def check_references(self) -> 'StoryDialog':
        """Check that the scene IDs and character nicknames in the dialogues are valid."""
        valid_scene_ids = self.valid_scene_ids
        valid_character_nicknames = self.valid_character_nicknames

        if not valid_character_nicknames:
            return self

        for act_dialog in self.act_dialogs:
            for scene_dialog in act_dialog.scene_dialogs:
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
    prompt: Optional[str] = Field("", description="Prompt or inspiration for the story")
    title: Optional[str] = Field("", description="Title of the story")
    video: Optional[bool] = Field(False, description="Whether the story is animated")
    visual_style: Optional[str] = Field("", description="Visual style of the story, e.g., 'Anime', 'Realistic'")
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

    # Private attribute to hold the reference to the associated StoryDialog
    _story_dialog: Optional['StoryDialog'] = PrivateAttr(default=None)

    def set_story_dialog(self, story_dialog: 'StoryDialog'):
        """
        Set the associated StoryDialog and establish a reverse reference.
        """
        self._story_dialog = story_dialog
        story_dialog._story = self  # Set reverse reference

    def get_story_dialog(self) -> Optional['StoryDialog']:
        """
        Get the associated StoryDialog.
        """
        return self._story_dialog

    @property
    def valid_character_nicknames(self) -> List[str]:
        """Get a list of valid character nicknames from the associated Story."""
        return [char.nickname or char.name.lower() for char in self.characters]

    @model_validator(mode='after')
    def check_references(self) -> 'Story':
        """Check that the character nicknames in the scene are valid."""
        valid_character_nicknames = self.valid_character_nicknames

        if not valid_character_nicknames:
            return self

        for act in self.acts:
            for scene in act.scenes:
                for character_involved in scene.characters_involved:
                    if character_involved.lower() not in valid_character_nicknames:
                        raise ValueError(f"Invalid character_nickname: {character_involved} in scene {scene.scene_id}")
        return self

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
        story_data = self.model_dump(exclude={"original_images", "revised_images"})
        json_path = os.path.join(directory_path, "story.json")
        with open(json_path, "w") as json_file:
            json.dump(story_data, json_file, indent=4)

        # Save the story_dialog if it exists
        if self._story_dialog is not None:
            # Save the StoryDialog data as JSON
            story_dialog_data = self._story_dialog.model_dump()
            story_dialog_json_path = os.path.join(directory_path, "story_dialog.json")
            with open(story_dialog_json_path, "w") as json_file:
                json.dump(story_dialog_data, json_file, indent=4)

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
            story.set_story_dialog(story_dialog)
        except FileNotFoundError:
            story_dialog = None  # No story_dialog found

        return story
    
    def load_story_dialog(self, directory_path: str) -> StoryDialog:
        """Load the associated StoryDialog from a directory containing a story_dialog.json file."""
        story_dialog_json_path = os.path.join(directory_path, "story_dialog.json")
        with open(story_dialog_json_path, "r") as json_file:
            story_dialog_data = json.load(json_file)
        return StoryDialog(**story_dialog_data)



# if __name__ == "__main__":
#     # Test the Story class
#     from pprint import pprint

#     print("Testing the Story class...")

#     example_story = Story(
#         prompt="A young wizard embarks on a quest to find a lost artifact.",
#         visual_style="Anime",
#         genre="Fantasy",
#         medium="Book",
#         title="The Wizard's Quest",
#         location="A magical realm",
#         plot_overview="A young wizard embarks on a dangerous quest to recover a lost artifact.",
#         characters=[
#             Character(
#                 name="Erion",
#                 description="A courageous young wizard.",
#                 personality="Brave but reckless.",
#                 physical_appearance="Tall with messy black hair.",
#                 gender="Male",
#                 age="Early 20s",
#                 catch_phrase="By the power of the elements!",
#                 # image=placeholder_image  # Placeholder PIL image for the character
#             ),
#             Character(
#                 name="Lyria",
#                 description="A mysterious sorceress.",
#                 personality="Calm and wise.",
#                 physical_appearance="Slender with silver hair.",
#                 gender="Female",
#                 age="30s",
#                 catch_phrase="Magic flows through all things.",
#                 # image=placeholder_image  # Placeholder PIL image for the character
#             )
#         ],
#         scenes=[
#             Scene(
#                 title="The Beginning of the Quest",
#                 description="Erion sets out from his village.",
#                 characters_involved=["Erion"],
#                 setting="A small village on the edge of a vast forest.",
#                 key_actions=["Erion begins his journey."],
#                 # image=placeholder_image  # Placeholder PIL image for the scene
#             )
#         ],
#         original_images=[
#             # placeholder_image  # Placeholder original PIL image
#         ],
#         revised_images=[
#             # placeholder_image  # Placeholder revised PIL image
#         ]
#     )

#     # Make sure we can marhsal and unmarshal the data
#     example_story_json = example_story.model_dump_json()
#     example_story_parsed = Story.model_validate_json(example_story_json)
#     pprint(example_story_parsed.model_dump())


