DEBUG = False

STORY_DIR = "stories/my_story"

# EXECUTE_EXAMPLES = True
EXECUTE_EXAMPLES = False

TEXT_MODEL_BACKEND = "ollama"
# TEXT_MODEL_BACKEND = "nim"

# TEXT_MODEL = "microsoft/Phi-3.5-mini-instruct" # ~7 GB VRAM
# TEXT_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct" # ~15.6 GB VRAM
# TEXT_MODEL = "meta-llama/Llama-3.1-8B-Instruct" # ~15.6 GB VRAM
# TEXT_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct"
# TEXT_MODEL = "meta-llama/Llama-3.2-3B-Instruct"
# TEXT_MODEL = "llama3.1"
# TEXT_MODEL = "llama3.1:70b"
TEXT_MODEL = "nemotron:70b"

TEXT_CONTEXT_WINDOW = 100000 # 128k for llama3.1

# NIM
# TEXT_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"



# DEVICE_MAP = "cuda"
# DEVICE_MAP = "cpu"
DEVICE_MAP = "auto"

import torch
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Temperature of 0 means deterministic output, while 1 means random output
TEMPERATURE = 0.0 # 0.6 is a good balance between randomness and coherence

# Top-p sampling to control output diversity (only used if temperature > 0)
# TOP_P = 0.9
TOP_P = 1

# Model that creates images from text
# Timestep-distilled - faster but has some limitations
# IMAGE_GENERATOR_MODEL = "black-forest-labs/FLUX.1-schnell" # About 33 GB VRAM?

# Guidence Distilled - focus on quality
IMAGE_GENERATOR_MODEL = "black-forest-labs/FLUX.1-dev" # About 33 GB VRAM?

# How many images to generate at once, depends on GPU memory and size of the images generated
IMAGE_GENERATION_BATCH_SIZE = 1

# Model that creates text from images to review whether the image was generated correctly
VISION_MODEL = "microsoft/Phi-3.5-vision-instruct" # Transformers
# VISION_MODEL = "meta-llama/Llama-3.2-11B-Vision" # Transformers
# VISION_MODEL = "meta-llama/Llama-3.2-11B-Vision-Instruct" # Transformers
# VISION_MODEL = "llama3.2-vision" # Ollama
# VISION_MODEL = "llama3.2-vision:90b" # Ollama
VISION_DEVICE_MAP = "auto"

MUSIC_MODEL = "facebook/musicgen-large"
# MUSIC_MODEL = "facebook/musicgen-medium"

# Model that creates short videos from images
VIDEO_GENERATOR_MODEL = "rain1011/pyramid-flow-sd3"

# ATTN_IMPLEMENTATION = None
ATTN_IMPLEMENTATION = "flash_attention_2"

# This might not be necessary
TOKENIZERS_PARALLELISM="true"

IMAGE_TO_VIDEO_MODEL = "THUDM/CogVideoX-5b-I2V"
# IMAGE_TO_VIDEO_MODEL = "ali-vilab/i2vgen-xl"
TEXT_TO_VIDEO_MODEL = 'THUDM/CogVideoX-5b'
IMAGE_TO_VIDEO_QUANTIZED = False
TEXT_TO_VIDEO_QUANTIZED = False

if "i2vgen-xl" in IMAGE_TO_VIDEO_MODEL:
    # Size for i2vgen-xl
    CHARACTER_ANIMATION_WIDTH = 1280
    CHARACTER_ANIMATION_HEIGHT = 704
else:
    # Size for CogVideoX-5b-I2V
    CHARACTER_ANIMATION_WIDTH = 720
    CHARACTER_ANIMATION_HEIGHT = 480


# https://huggingface.co/docs/accelerate/en/usage_guides/model_size_estimator for estimating model size

# !export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True