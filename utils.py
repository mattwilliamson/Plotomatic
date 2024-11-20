from model import *
from typing import List
from pydantic import BaseModel
import torch
import difflib
import random
import textwrap
from llama_index.core.llms import ChatMessage
import numpy as np
import time
import ipywidgets as widgets
from IPython.display import display, clear_output, Markdown

def chat_message_to_dict(message: ChatMessage) -> dict:
    # Use model_dump to get the dictionary representation and adjust the role
    message_dict = message.model_dump()
    message_dict['role'] = message_dict['role'].value  # Convert enum to string
    return message_dict

def chat_messages_to_dicts(messages: List[ChatMessage]) -> List[dict]:
    return [chat_message_to_dict(message) for message in messages]


def deindent(text: str) -> str:
    """Remove leading whitespace from each line of text."""
    return textwrap.dedent(text).strip()

def merge_models(obj1: BaseModel, obj2: BaseModel) -> Story:
    """
    Take two BaseModel objects (e.g., Story or StoryDialog), make a copy of the first,
    and update the copy with any non-empty values from the second, recursively.
    """
    # Copy the first object to avoid mutating the original
    obj_copy = obj1.copy()

    def update_recursive(target, source):
        if isinstance(target, BaseModel) and isinstance(source, BaseModel):
            for field in source.model_fields:
                value1 = getattr(target, field, None)
                value2 = getattr(source, field, None)
                if value2 not in [None, "", [], {}]:
                    if isinstance(value1, BaseModel) and isinstance(value2, BaseModel):
                        update_recursive(value1, value2)
                    elif isinstance(value1, list) and isinstance(value2, list):
                        update_list(value1, value2)
                    else:
                        setattr(target, field, value2)
        elif isinstance(target, list) and isinstance(source, list):
            update_list(target, source)

    def update_list(list1: List, list2: List):
        """
        Update list1 based on values in list2.
        """
        for i, value2 in enumerate(list2):
            if i < len(list1):
                value1 = list1[i]
                if isinstance(value1, BaseModel) and isinstance(value2, BaseModel):
                    update_recursive(value1, value2)
                else:
                    list1[i] = value2
            else:
                # Append new items from list2 that aren't in list1
                list1.append(value2)

    update_recursive(obj_copy, obj2)
    return obj_copy

def show_diff(story1: Story, story2: Story):
    """Show the differences between two Story objects in a python notebook."""
    story1_json = story1.model_dump_json(indent=2, exclude_defaults=True)
    story2_json = story2.model_dump_json(indent=2, exclude_defaults=True)

    left, right = story1_json.splitlines(), story2_json.splitlines()

    # Calculate the number of lines in the diff output so we can show the whole json doc, not just the diff
    total_lines = max(len(left), len(right))

    diff = difflib.unified_diff(left, right, lineterm='', n=total_lines, fromfile='story.json', tofile='new_story.json')
    diff_text = '\n'.join(diff)
    # display(Markdown(f'```json\n{story1_json}\n```'))
    # display(Markdown(f'```json\n{story2_json}\n```'))
    display(Markdown(f'```diff\n{diff_text}\n```'))


def set_torch_seed(seed: int):
    if seed < 0:
        seed = -seed
    if seed > (1 << 31):
        seed = 1 << 31

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)

    if torch.backends.cudnn.is_available():
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


class ProgressTracker:
    def __init__(self, max_items: int, description: str = "Progress"):
        """
        Initialize the progress tracker.

        Args:
            max_items (int): The total number of items to process.
        """
        self._max = max_items
        self._value = 0
        self._description = description
        self.start_time = time.time()

        # Widgets for the progress bar and additional information
        self.progress_bar = widgets.IntProgress(
            value=self._value, min=0, max=self._max,
            description=self._description,
            layout=widgets.Layout(width="100%")
        )
        self.status_display = widgets.HTML(value="")
        self.time_display = widgets.HTML(value="")

        # Display widgets
        display(self.progress_bar)
        display(self.status_display)
        display(self.time_display)

    # Simulate widgets.IntProgress properties
    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, new_value: int):
        if not (0 <= new_value <= self._max):
            raise ValueError(f"value must be between 0 and {self._max}")
        self._value = new_value
        self.current_items = self._value  # Sync with current_items for display updates
        self._update_display()

    @property
    def max(self) -> int:
        return self._max

    @max.setter
    def max(self, new_max: int):
        if new_max < 0:
            raise ValueError("max must be a positive integer")
        self._max = new_max
        self.progress_bar.max = self._max  # Update the progress bar's maximum

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, new_description: str):
        self._description = new_description
        self.progress_bar.description = self._description

    def update(self, items_done: int = 1):
        """
        Update the progress tracker with the number of items completed.

        Args:
            items_done (int): The number of additional items completed.
        """
        self.value += items_done

    def set_items_done(self, items_done: int):
        """
        Set the number of items done directly.

        Args:
            items_done (int): The total number of items completed so far.
        """
        self.value = items_done

    def _update_display(self):
        """
        Update the progress bar and associated displays.
        """
        # Update the progress bar
        self.progress_bar.value = self._value

        # Update the status display
        items_left = self._max - self._value
        self.status_display.value = f"<b>{self._value} done / {self._max} total ({items_left} left)</b>"

        # Update the time remaining display
        elapsed_time = time.time() - self.start_time
        if self._value > 0:
            avg_time_per_item = elapsed_time / self._value
            estimated_time_remaining = avg_time_per_item * items_left
            self.time_display.value = (
                f"<b>Time Remaining:</b> {self._format_time(estimated_time_remaining)}"
            )
        else:
            self.time_display.value = "<b>Time Remaining:</b> Calculating..."

    def _format_time(self, seconds: float) -> str:
        """
        Format time in seconds into a human-readable string.

        Args:
            seconds (float): The number of seconds.

        Returns:
            str: Formatted time as HH:MM:SS.
        """
        minutes, sec = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{sec:02}"

    def finish(self):
        """
        Mark the progress tracker as complete.
        """
        self.value = self._max
        self.time_display.value = "<b>Time Remaining:</b> Completed!"
        self.progress_bar.bar_style = "success"

    def reset(self):
        """
        Reset the progress tracker to its initial state.
        """
        self._value = 0
        self.start_time = time.time()
        self._update_display()

        # Reset the progress bar and status displays
        self.progress_bar.value = self._value
        self.progress_bar.bar_style = ""  # Reset bar style to default
        self.status_display.value = f"<b>0 done / {self._max} total ({self._max} left)</b>"
        self.time_display.value = "<b>Time Remaining:</b> Calculating..."




blank_story = Story(
    # themes=[],
    # motifs=[],
    characters=[
        Character(
            nickname="character1",
            name="",
            description="",
            personality="",
            physical_appearance="",
            role="",
            age="",
            catch_phrase="",
            relationships=[CharacterRelationship(name="", relationship="", description="")],
            internal_conflict="",
            character_arc=CharacterArc(initial_state="", final_state="", key_moments=[""]),
        ),
    ],
    acts=[
        Act(
            act_id="act1",
            props=[""],
            chapters=[
                Chapter(
                    chapter_id="chapter1",
                    scenes=[
                        Scene(
                            scene_id="scene1",
                            characters_involved_nicknames=["character1"],
                            props=[""],
                            key_actions=[""],
                        ),
                    ],
                ),
            ],
        ),
    ],
    props=[
        Prop(
            name="",
            description="",
            physical_appearance="",
            purpose="",
        ),
    ],
    subplots=[Subplot(
        key_events=[""],
    )],
    emotional_arc=[
        EmotionalArc(
            key_moments=[""],
        ),
    ],
    story_beats=[
        StoryBeat(
            key_actions=[""],
        ),
    ],
)

blank_story_dialog = StoryDialogue(
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
                                    character_nickname="character1",
                                    line="",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ],
)

# Associate the blank story and story dialog with each other
blank_story.set_story_dialogue(blank_story_dialog)

