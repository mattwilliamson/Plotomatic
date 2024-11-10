Plot-o-matic Story Generator
---



Write a grapphic novel with one prompt!

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

- [LlamaIndex](https://docs.llamaindex.ai/en/stable/examples/llm/nvidia_nim/) - used to generate chapters/scnees while maintaining coherence
- [NeMo Guardrails](https://docs.nvidia.com/nemo/guardrails/) - Prevent NSFW and enforce JSON output
- [NIM microservice](https://build.nvidia.com/explore/discover) - For serving LLNs locally
- [Nemotron 70b](https://build.nvidia.com/nvidia/llama-3_1-nemotron-70b-instruct) - LLM for NIM
- [Flux.1-dev](https://huggingface.co/black-forest-labs/FLUX.1-dev) for image creation
- [CogVideoX-5b-I2V](https://huggingface.co/THUDM/CogVideoX-5b-I2V) - Text/image to video
- [Parler-TTS](https://github.com/huggingface/parler-tts) for speech creation
- [fish-speech](https://github.com/fishaudio/fish-speech) OR [CoquiTTS](https://github.com/coqui-ai/TTS) for speech cloning
- [Musigen](https://huggingface.co/facebook/musicgen-large) for music

## Step-by-Step Process to Generate a Story Using LLM Models

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

### [Step 13](./13_music.ipynb)
- Music for each scene


---


### Beyond
- Critique images using vision model
- Regenerate any flagged images
- Display original and revised images
- Assemble the final story (text + images)
- Output the final story in the desired format
