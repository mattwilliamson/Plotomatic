from llama_index.core.extractors import BaseExtractor
from typing import List, Any, Sequence, Dict
from llama_index.core.schema import BaseNode, TextNode
from llama_index.core.llms.llm import LLM
from llama_index.core.prompts import PromptTemplate
from llama_index.core.async_utils import DEFAULT_NUM_WORKERS, run_jobs
from llama_index.core.bridge.pydantic import (
    Field,
    PrivateAttr,
    SerializeAsAny,
)

from story_extractor import extract_story_json
# extract_story_json(llm: LLM, input: str)

DEFAULT_CHARACTER_EXTRACT_TEMPLATE = """\
Here is the content of the section:
{context_str}

List all of the characters, including name, description, personality, physical_appearance, role, gender, age, voice_description, relationships, internal_conflict
If something is not specified, you can leave it blank.

Example Character:

name: Pip the Penguin
description: A curious and adventurous young penguin with a big imagination, always dreaming of exploring the world
personality: Brave, imaginative, and kind-hearted
physical_appearance: A small penguin with a distinctive red scarf
role: Protagonist
internal_conflict: Pip often feels nervous about the unknown but learns to overcome his fears with Sally's support.
relationships:
- Sally the Seal, Best Friend, Sally is Pip's loyal and clever friend who accompanies him

Characters: """


class CharacterExtractor(BaseExtractor):
    """
    Character extractor. Node-level extractor.
    """

    llm: SerializeAsAny[LLM] = Field(description="The LLM to use for generation.")
    prompt_template: str = Field(
        default=DEFAULT_CHARACTER_EXTRACT_TEMPLATE,
        description="Template to use when generating characters.",
    )

    def __init__(
        self,
        llm: LLM,
        prompt_template: str = DEFAULT_CHARACTER_EXTRACT_TEMPLATE,
        num_workers: int = DEFAULT_NUM_WORKERS,
        **kwargs: Any,
    ):
        super().__init__(
            llm=llm,
            prompt_template=prompt_template,
            num_workers=num_workers,
            **kwargs,
        )

    @classmethod
    def class_name(cls) -> str:
        return "CharacterExtractor"

    async def _agenerate_node_characters(self, node: BaseNode) -> str:
        """Generate a character list for a node."""
        if self.is_text_node_only and not isinstance(node, TextNode):
            return ""

        context_str = node.get_content(metadata_mode=self.metadata_mode)
        summary = await self.llm.apredict(
            PromptTemplate(template=self.prompt_template), context_str=context_str
        )

        return summary.strip()

    async def aextract(self, nodes: Sequence[BaseNode]) -> List[Dict]:
        if not all(isinstance(node, TextNode) for node in nodes):
            raise ValueError("Only `TextNode` is allowed for `Character` extractor")

        node_summaries_jobs = []
        for node in nodes:
            node_summaries_jobs.append(self._agenerate_node_characters(node))

        node_characters = await run_jobs(
            node_summaries_jobs,
            show_progress=self.show_progress,
            workers=self.num_workers,
        )

        # Extract node-level summary metadata
        metadata_list: List[Dict] = [{} for _ in nodes]
        for i, metadata in enumerate(metadata_list):
            metadata["characters"] = node_characters[i]

        return metadata_list




DEFAULT_SCENE_EXTRACT_TEMPLATE = """\
Here is the content of the section:
{context_str}

List all of the scenes, including \
    title, description, characters_involved, setting, time_of_day, location, lighting, mood, props, key_actions

If something is not specified, you can leave it blank.

Example Scene:

title: Finding the Map
description: Pip stumbles upon a bottle washed ashore, containing an old map
characters_involved: 
    - Pip
    - Sally
setting: The icy shore near Pip's colony
time_of_day: Morning
location: Penguin Colony Shore
lighting: Bright sunlight reflecting off the icy sea
mood: Excited and full of wonder
props: 
    - The Treasure Map
key_actions: 
    - Pip holds the map up, showing Sally the exciting adventure ahead

Scenes: """


class SceneExtractor(BaseExtractor):
    """
    Scene extractor. Node-level extractor.
    """

    llm: SerializeAsAny[LLM] = Field(description="The LLM to use for generation.")
    prompt_template: str = Field(
        default=DEFAULT_SCENE_EXTRACT_TEMPLATE,
        description="Template to use when generating scenes.",
    )

    def __init__(
        self,
        llm: LLM,
        prompt_template: str = DEFAULT_SCENE_EXTRACT_TEMPLATE,
        num_workers: int = DEFAULT_NUM_WORKERS,
        **kwargs: Any,
    ):
        super().__init__(
            llm=llm,
            prompt_template=prompt_template,
            num_workers=num_workers,
            **kwargs,
        )

    @classmethod
    def class_name(cls) -> str:
        return "SceneExtractor"

    async def _agenerate_node_scenes(self, node: BaseNode) -> str:
        """Generate a scene list for a node."""
        if self.is_text_node_only and not isinstance(node, TextNode):
            return ""

        context_str = node.get_content(metadata_mode=self.metadata_mode)
        summary = await self.llm.apredict(
            PromptTemplate(template=self.prompt_template), context_str=context_str
        )

        return summary.strip()

    async def aextract(self, nodes: Sequence[BaseNode]) -> List[Dict]:
        if not all(isinstance(node, TextNode) for node in nodes):
            raise ValueError("Only `TextNode` is allowed for `Scene` extractor")

        node_summaries_jobs = []
        for node in nodes:
            node_summaries_jobs.append(self._agenerate_node_scenes(node))

        node_scenes = await run_jobs(
            node_summaries_jobs,
            show_progress=self.show_progress,
            workers=self.num_workers,
        )

        # Extract node-level summary metadata
        metadata_list: List[Dict] = [{} for _ in nodes]
        for i, metadata in enumerate(metadata_list):
            metadata["scenes"] = node_scenes[i]

        return metadata_list


class StoryExtractor(BaseExtractor):
    """
    Story extractor. Node-level extractor.
    """

    llm: SerializeAsAny[LLM] = Field(description="The LLM to use for generation.")

    def __init__(
        self,
        llm: LLM,
        num_workers: int = DEFAULT_NUM_WORKERS,
        **kwargs: Any,
    ):
        super().__init__(
            llm=llm,
            num_workers=num_workers,
            **kwargs,
        )

    @classmethod
    def class_name(cls) -> str:
        return "StoryExtractor"

    async def _agenerate_node_stories(self, node: BaseNode) -> str:
        """Generate a story list for a node."""
        if self.is_text_node_only and not isinstance(node, TextNode):
            return ""

        context_str = node.get_content(metadata_mode=self.metadata_mode)
        summary = await self.llm.apredict(
            PromptTemplate(template=self.prompt_template), context_str=context_str
        )

        return summary.strip()

    async def aextract(self, nodes: Sequence[BaseNode]) -> List[Dict]:
        if not all(isinstance(node, TextNode) for node in nodes):
            raise ValueError("Only `TextNode` is allowed for `STORY` extractor")

        node_summaries_jobs = []
        for node in nodes:
            node_summaries_jobs.append(self._agenerate_node_stories(node))

        node_stories = await run_jobs(
            node_summaries_jobs,
            show_progress=self.show_progress,
            workers=self.num_workers,
        )

        # Extract node-level summary metadata
        metadata_list: List[Dict] = [{} for _ in nodes]
        for i, metadata in enumerate(metadata_list):
            metadata["stories"] = node_stories[i]

        return metadata_list
