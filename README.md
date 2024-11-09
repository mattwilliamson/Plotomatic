Plot-o-matic Story Generator
---

Use LLMs to generate compelling stories in different mediums in an automated fashion.

# Samples

## Robot Ninja Gif
Prompt: 
> A video game: In a futuristic world, a team of rogue robot ninjas must overthrow their corrupt AI overlords to reclaim their freedom and save humanity.
![Robot Ninja](./samples/kaito.cog.gif)

## 8bit Video Game Gif
Prompt:
> 8-bit Video Game
![8bit game](./samples/8_bit_fight_svd.gif)

## Video with voiceover
Prompt:
> A fantasy live action movie: A blonde haired blue eyed knight named Matt must journey to the center of the world to forge a magical weapon capable of defeating an ancient dragon and saving the babe princess and kingdom. The Princess Ashley has brown hair and blue eyes and wears glasses with thick rims.
[Sample Video](./samples/princess.mp4)

## Audio Voiceover
Prompt:
> Calm and authoritative, with a hint of warmth.
[Sample Audio](./samples/dr_elara.wav)


# Technologies

- LlamaIndex - used to generate chapters/scnees while maintaining coherence
- NIM microservice - For serving LLNs locally
- NeMo Guardrails - Prevent NSFW and enforce JSON outut
- Nemotron 70b - LLM
- CogVideoX - Text/image to video

## Step-by-Step Process to Generate a Story Using LLM Models

TODO: Break up text generation vs image generation

- Data model to pass details about the story around as context
- User input: "A young wizard embarks on a quest to find a lost artifact."

### [Step 0](./0_install_prepreqs.ipynb)
- Setup conda env
- Install conda packages
- Install pip packages

### [Step 0](./0_test_llm.ipynb)
- Compare the creativity of different models
    * **nemotron:70b** - this one is arbitrarily my favorite
    * hermes3:70b
    * llama3.1:70b
    * gemma2:27b
    * mistral-openorca:7b
    * ~~qwen2.5:72b~~
    * ~~phi3.5~~

### *[Step 1](./1_generate_samples.ipynb) (WIP)*
- UseLlamaIndex to generate summaries from real literature to use as few-shot examples 

### [Step 2](./2_title_plot.ipynbb)
- Generate plot summary
- Generate story title
- Decide Genre + Medium + Visual Style

### [Step 3](./3_character_descriptions.ipynb)
- Generate a list characters and descriptions

### [Step 4](./4_scene_descriptions.ipynb)
- Generate a list of scenes

### [Step 5](./5_character_images.ipynb)
- Generate images for characters

### [Step 6](./6_scene_images.ipynb)
- Generate scene images

### [Step 7](./7_character_animated.ipynb)
- Generate animations for character images

### *[Step 8](./8_prop_descriptions.ipynb) (WIP)*
- Generate a list of props

### *[Step 9](./9_prop_images.ipynb) (WIP)*
- Generate prop images

### *[Step 10](./10_sprite_extraction.ipynb) (WIP)*
- Extract sprites

### [Step 11](./11_character_voice.ipynb)
- Character voice baseline for grounding
- Character voice clone

### [Step 12](./12_character_video.ipynb)
- Make video from audio and video clips and combine them with ffmpeg


---


### Beyond
- Critique images using vision model
- Regenerate any flagged images
- Display original and revised images
- Assemble the final story (text + images)
- Output the final story in the desired format
