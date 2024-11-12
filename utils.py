from model import *
from typing import List
from pydantic import BaseModel
import torch
import difflib
import random
from IPython.display import Markdown, display
import textwrap
from llama_index.core.llms import ChatMessage
import numpy as np

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
            scenes=[
                Scene(
                    scene_id="scene1",
                    characters_involved=["character1"],
                    props=[""],
                    key_actions=[""],
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
            dialogues=[
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
)

# Associate the blank story and story dialog with each other
blank_story.set_story_dialogue(blank_story_dialog)