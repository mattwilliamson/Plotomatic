# **:clapper: Plot-o-matic Story Generator :clapper:**

Transform your story ideas into immersive graphic novels, animations, and audio experiences—all from a single prompt!

![Banner](./src/plotomatic/static/banner.jpg)

## :rocket: Write an Entire Graphic Novel with One Prompt!

Dive into a world where a single idea sparks entire universes. From rogue ninjas overthrowing AI overlords to epic knights on mystical quests, Plot-o-matic Story Generator brings your story to life across various media—quickly, creatively, and with endless customization options.

### :star2: **Story Samples**

Here are some examples of what Plot-o-matic can generate:

---

### :robot: **Robot Ninja** *(GIF)*
Prompt: 
> A video game: In a futuristic world, a team of rogue robot ninjas must overthrow their corrupt AI overlords to reclaim their freedom and save humanity.

![Robot Ninja](./src/plotomatic/static/kaito.cog.gif)

---

### :video_game: **8-bit Video Game** *(GIF)*
Prompt:
> 8-bit Video Game

![8bit game](./src/plotomatic/static/8_bit_fight_svd.gif)

---

### :microphone: **Voiceover** *(Audio)*
Prompt:
> Calm and authoritative, with a hint of warmth.

[Sample Audio :headphones:](./src/plotomatic/static/dr_elara.wav)

---

### :musical_note: **Suspenseful Music** *(Music)*
Prompt:
> Tense and suspenseful.

[Sample Music :musical_note:](./src/plotomatic/static/tense_focused.wav)

---

### :european_castle: **Fantasy Knight Adventure** *(Video with Voiceover)* 
Prompt:
> A fantasy live-action movie: A blonde-haired, blue-eyed knight named Matt must journey to the center of the world to forge a magical weapon capable of defeating an ancient dragon and saving the princess and kingdom.

[Sample Video :arrow_forward:](./src/plotomatic/static/princess.mp4)

---

## :book: **About the Project**

Plot-o-matic combines the power of AI to turn any story idea into a wide variety of storytelling formats:

- Graphic Novels & Books
- Short Films
- Podcasts & Audio Dramas
- Comics
- Video Game Storylines & Assets
- Plays
- Cartoons & animations
- Documentaries
- Song Lyrics and much more!

## :hammer_and_wrench: **Technologies**

We leverage a suite of AI tools to bring your stories to life:

- [LlamaIndex](https://docs.llamaindex.ai/en/stable/examples/llm/nvidia_nim/) :dromedary_camel: - used to generate chapters/scenes while maintaining coherence
- [NeMo Guardrails](https://docs.nvidia.com/nemo/guardrails/) - Prevent NSFW and enforce JSON output
- [NIM microservice](https://build.nvidia.com/explore/discover) - For serving LLMs locally or using NVIDIA NIM in the cloud
- [Nemotron 70b](https://build.nvidia.com/nvidia/llama-3_1-nemotron-70b-instruct) - LLM for NIM
- [Flux.1-dev](https://huggingface.co/black-forest-labs/FLUX.1-dev) for image creation
- [CogVideoX-5b-I2V](https://huggingface.co/THUDM/CogVideoX-5b-I2V) - Text/image to video
- [Parler-TTS](https://github.com/huggingface/parler-tts) for speech creation
- [fish-speech](https://github.com/fishaudio/fish-speech) OR [CoquiTTS](https://github.com/coqui-ai/TTS) for speech cloning
- [Musigen](https://huggingface.co/facebook/musicgen-large) for music


# Run Plotomatic

```sh
conda create -n plotomatic python=3.12
conda activate plotomatic

# Install the package in development mode
cd /path/to/plotomatic-streamlit  # Directory containing pyproject.toml
pip install -e .                  # Basic installation
# OR
pip install -e ".[dev]"          # Install with development dependencies

# Run the Streamlit app
streamlit run src/plotomatic/Home.py
```

Open http://localhost:8501 in your browser.




## :memo: **Step-by-Step Notebooks**

### [view_plot.ipynb](./view_plot.ipynb)
- **Review and Evolve the Plot**

This notebook provides tools to visualize and track the story's development. After each generation step, you can revisit this notebook to review the evolving plot through detailed overviews, interactive diagrams, and other visualization tools. 

As you refine the story prompt or adjust the model's settings, use this notebook to see how those changes impact the narrative structure. With each re-run, observe how characters, themes, and events unfold differently—allowing you to shape and perfect the story iteratively.

---

### [0_install_prepreqs.ipynb](./0_install_prepreqs.ipynb)
- Set up conda env
- Install conda packages
- Install pip packages

### [1_story_prompt.ipynb](./1_story_prompt.ipynb)
- Set the input prompt for the story and kick it off

### [2_title_plot.ipynbb](./2_title_plot.ipynbb)
- Generate plot summary
- Generate story title
- Decide Genre + Medium + Visual Style

### [3_character_descriptions.ipynb](./3_character_descriptions.ipynb)
- Generate a list of characters and descriptions

### [4_scene_descriptions.ipynb](./4_scene_descriptions.ipynb)
- Generate a list of scenes

### [5_character_images.ipynb](./5_character_images.ipynb)
- Generate images for characters

### [6_scene_images.ipynb](./6_scene_images.ipynb)
- Generate scene images

### [7_character_animated.ipynb](./7_character_animated.ipynb)
- Generate animations for character images

### *[8_prop_descriptions.ipynb](./8_prop_descriptions.ipynb)* (WIP :construction:)
- Generate a list of props

### *[9_prop_images.ipynb](./9_prop_images.ipynb)* (WIP :construction:)
- Generate prop images

### :sparkles: *[10_sprite_extraction.ipynb](./10_sprite_extraction.ipynb)* (WIP :construction:)
- Extract sprites

### :microphone: [11_character_voice.ipynb](./11_character_voice.ipynb)
- Character voice baseline for grounding
- Character voice clone

### [12_character_video.ipynb](./12_character_video.ipynb)
- Make video from audio and video clips and combine them with ffmpeg

### :musical_note: [13_music.ipynb](./13_music.ipynb)
- Music for each scene

---

### [test_llm.ipynb](./test_llm.ipynb)
- Compare the creativity of different models
- **nemotron:70b** - This one is arbitrarily my favorite

### *[generate_samples.ipynb](./generate_samples.ipynb)* (WIP :construction:)
- Use LlamaIndex to generate summaries from real literature to use as few-shot examples 



## TODO:
- Plot Diagram
- Generate screenplay
- Gallery
- Move voice description to separate step
- Improve animation descriptions
- Voice description should describe better like: "A youthful male voice with a distinct Latin American accent speaks clearly and energetically. The tone is persuasive and determined, occasionally revealing subtle hints of vulnerability. The speaker's voice has a warm timbre with a slight melodic lilt typical of Latin American Spanish speakers. The speech pattern includes softened consonants and rhythmic intonation. The audio quality is exceptionally high, with a close-up feel that captures the nuances of the voice, including breath control and subtle vocal inflections. The overall delivery is dynamic and engaging, with emphasis on key words to enhance persuasiveness."
- Give the LLM creative freedom by letting them put in the chapter titles
- Select different renderers based on the media

## :file_folder: Project Structure

```
src/
├── plotomatic/
│   ├── __init__.py
│   ├── app.py
│   ├── Home.py              # Main Streamlit entry point
│   ├── components/          # Reusable UI components
│   │   ├── __init__.py
│   │   ├── project_selector.py
│   │   ├── diff_viewer.py
│   │   ├── json_editor_tab.py
│   │   └── sidebar.py
│   ├── config/             # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── core/              # Core application logic
│   │   ├── __init__.py
│   │   └── tools.py
│   ├── llm/               # LLM integration
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── ollama_logging.py
│   ├── models/            # Pydantic data models
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── story.py
│   │   ├── story_dialogue.py
│   │   └── chat.py
│   ├── pages/             # Streamlit pages
│   │   ├── __init__.py
│   │   ├── select_project.py
│   │   └── start_story.py
│   ├── project_manager/   # Project management
│   │   ├── __init__.py
│   │   └── manager.py
│   ├── static/           # Static assets
│   │   ├── images/
│   │   ├── audio/
│   │   └── video/
│   ├── tests/            # Test suite
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── pages/
│   └── utils/            # Utility functions
│       ├── __init__.py
│       ├── debug_logger.py
│       ├── git_utils.py
│       └── helpers.py
├── tests/                # Integration tests
│   └── ...
├── .gitignore
├── pyproject.toml        # Project configuration
├── README.md
└── requirements.txt
```

## :gear: Development

### Installation

```sh
# Create and activate conda environment
conda create -n plotomatic python=3.12
conda activate plotomatic

# Install in development mode with all dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```sh
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=plotomatic

# Run specific test file
pytest src/plotomatic/tests/pages/test_title_plot.py
```

### Code Quality

```sh
# Format code
black src/plotomatic

# Sort imports
isort src/plotomatic

# Type checking
mypy src/plotomatic
```

### Run Application

```sh
# Run the Streamlit app
streamlit run src/plotomatic/Home.py
```

Open http://localhost:8501 in your browser.

> **Development Mode**: The `-e` flag installs the package in "editable" mode, which means:
> - You can modify source files and test changes immediately
> - No need to reinstall after changes
> - Python will use your working directory files directly
> - Perfect for development and testing