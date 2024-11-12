
# See https://huggingface.co/docs/diffusers/en/api/pipelines/flux for more info
# also https://huggingface.co/docs/diffusers/v0.18.2/en/api/pipelines/stable_diffusion/stable_diffusion_xl
# https://huggingface.co/docs/diffusers/main/en/api/pipelines/overview#diffusers.DiffusionPipeline

import settings

from diffusers import FluxPipeline
import torch
from PIL import Image
import matplotlib.pyplot as plt
import gc
from diffusers import FluxTransformer2DModel, FluxPipeline
from transformers import T5EncoderModel, CLIPTextModel
from optimum.quanto import freeze, qfloat8, quantize

# Load the Flux model
pipe_image = FluxPipeline.from_pretrained(settings.IMAGE_GENERATOR_MODEL, torch_dtype=torch.bfloat16)

# Get the list of available GPUs and their memory
# torch_device_map = {i: f"{torch.cuda.get_device_properties(i).total_memory // (1024 ** 3)}GiB" for i in range(torch.cuda.device_count())}
# torch_device_map["cpu"] = "32GiB"
# pipe_image = FluxPipeline.from_pretrained(
#     settings.IMAGE_GENERATOR_MODEL, 
#     torch_dtype=torch.bfloat16,
#     device_map="balanced", 
#     max_memory=torch_device_map,
# )


# pipe_image = pipe_image.to(settings.DEVICE)

# Offloads all models to CPU using accelerate, reducing memory usage with a low impact on performance.
pipe_image.enable_model_cpu_offload()

# Memory savings are higher than with `enable_model_cpu_offload`, but performance is lower
# pipe_image.enable_sequential_cpu_offload()

# When this option is enabled, the VAE will split the input tensor in slices to compute decoding in several steps. This is useful to save some memory and allow larger batch sizes.
pipe_image.vae.enable_slicing()

# When this option is enabled, the VAE will split the input tensor into tiles to compute decoding and encoding in several steps. This is useful to save a large amount of memory and to allow the processing of larger images.
pipe_image.vae.enable_tiling()


from typing import Union
from typing import List, Optional
from IPython.display import display

def generate_image(prompt: Union[str, List[str]] = None, prompt2: Union[str, List[str]] = None, height: float = None, width: float = None, guidance_scale: float = 0.0) -> Image:
    """Generate an image based on a free text prompt input."""

    # default to Timestep-distilled model
    pipe_kwargs = {
        "guidance_scale": 0.0,
        "num_inference_steps": 4,
        "max_sequence_length": 256,
    }

    # overrides for Guidance-distilled model
    if "FLUX.1-dev" in settings.IMAGE_GENERATOR_MODEL:
        pipe_kwargs = {
            "guidance_scale": 3.5,
            "num_inference_steps": 50
        }

    if guidance_scale:
        pipe_kwargs["guidance_scale"] = guidance_scale

    if prompt2:
        prompt = prompt if len(prompt) > len(prompt2) else prompt2

    pipe_kwargs["prompt"] = prompt
    # pipe_kwargs["prompt2"] = prompt2 or prompt
    pipe_kwargs["height"] = height
    pipe_kwargs["width"] = width
    
    if settings.TEMPERATURE == 0.0:
        pipe_kwargs["generator"] = torch.Generator("cpu").manual_seed(0)

    images = pipe_image(**pipe_kwargs).images
      
    if isinstance(prompt, str):
        return images[0]
    
    return images


def show_image_grid(images, main_title=None, titles=None):
    """Display a list of images as a grid with an optional main title.
    if images is a dictionary, the keys will be used as titles for each image."""
    if isinstance(images, dict):
        titles = list(images.keys())
        images = list(images.values())

    # Split images into a list of lists where each sublist has at most 4 images
    image_grid = [images[i:i + 4] for i in range(0, len(images), 4)]

    # Calculate the number of rows and columns
    num_rows = len(image_grid)
    num_cols = 4

    # Create the figure and axes grid
    fig, axes = plt.subplots(num_rows, num_cols, figsize=(20, 5 * num_rows))

    # Set the main title if provided
    if main_title:
        fig.suptitle(main_title, fontsize=16)

    # Iterate over the grid of images
    for i, row in enumerate(image_grid):
        for j in range(num_cols):
            ax = axes[i, j] if num_rows > 1 else axes[j]
            if j < len(row):
                # Show the image in the appropriate subplot
                ax.imshow(row[j])
                if titles:
                    ax.set_title(titles[i * num_cols + j], fontsize=12)
            # Turn off the axis for all subplots
            ax.axis('off')

    # Adjust the layout to prevent overlap
    plt.tight_layout()
    plt.subplots_adjust(top=0.9)  # Adjust top to fit the main title
    plt.show()

def free_memory():
    """Free memory up after running the text model"""
    print('Max mem allocated (GB) while doing text model:', torch.cuda.max_memory_allocated() / (1024 ** 3))

    from numba import cuda
    device = cuda.get_current_device()
    device.reset()

    # # Step 1: Delete all references to the models and pipelines
    # try:
    #     del pipe_image
    # except:
    #     pass

    # # Step 2: Run garbage collection to free up Python memory references
    # gc.collect()

    # # Step 3: Empty the CUDA cache to free memory back to PyTorch
    # torch.cuda.empty_cache()

    # # Step 4 (Optional): Synchronize CUDA to ensure all operations are complete
    # torch.cuda.synchronize()
