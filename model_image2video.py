import settings
import torch
from IPython.display import Video, display
from diffusers.utils import export_to_gif, export_to_video
# from IPython.display import Image as IPImage
from PIL import Image
from typing import List

# https://huggingface.co/docs/diffusers/main/en/api/pipelines/overview#diffusers.DiffusionPipeline
# https://huggingface.co/docs/diffusers/main/en/api/pipelines/cogvideox
# https://huggingface.co/THUDM/CogVideoX-5b-I2V

model_name = settings.IMAGE_TO_VIDEO_MODEL

kwargs = dict(
    num_videos_per_prompt=1,
    num_inference_steps=50,
    num_frames=49,
    generator=torch.Generator(device="cuda").manual_seed(42),
)

if "CogVideoX" in model_name:
    # kwargs['num_inference_steps'] = 50
    kwargs['num_frames'] = 49
    kwargs['generator'] = torch.Generator(device="cuda").manual_seed(42)

    if settings.IMAGE_TO_VIDEO_QUANTIZED:
        # Quantized
        from diffusers import AutoencoderKLCogVideoX, CogVideoXTransformer3DModel, CogVideoXImageToVideoPipeline
        from transformers import T5EncoderModel
        from torchao.quantization import quantize_, int8_weight_only

        quantization = int8_weight_only

        text_encoder = T5EncoderModel.from_pretrained(model_name, subfolder="text_encoder", torch_dtype=torch.bfloat16)
        quantize_(text_encoder, quantization())

        transformer = CogVideoXTransformer3DModel.from_pretrained(model_name, subfolder="transformer", torch_dtype=torch.bfloat16)
        quantize_(transformer, quantization())

        vae = AutoencoderKLCogVideoX.from_pretrained(model_name, subfolder="vae", torch_dtype=torch.bfloat16)
        quantize_(vae, quantization())

        # Create pipeline and run inference
        pipe = CogVideoXImageToVideoPipeline.from_pretrained(
            model_name,
            text_encoder=text_encoder,
            transformer=transformer,
            vae=vae,
            torch_dtype=torch.bfloat16,
        )

        pipe.enable_model_cpu_offload()
        pipe.vae.enable_tiling()
        pipe.vae.enable_slicing()

            
    else:
        # Not Quantized
        from diffusers import CogVideoXImageToVideoPipeline

        prompt = "A little girl is riding a bicycle at high speed. Focused, detailed, realistic."
        pipe = CogVideoXImageToVideoPipeline.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16
        )

        pipe.enable_sequential_cpu_offload()
        pipe.vae.enable_slicing()
        pipe.vae.enable_tiling()


elif "i2vgen-xl" in model_name:
    # i2vgen-xl
    from diffusers import I2VGenXLPipeline

    pipe = I2VGenXLPipeline.from_pretrained(model_name, torch_dtype=torch.float16, variant="fp16")

    # For lower memory
    pipe.enable_model_cpu_offload()

    kwargs['generator'] = torch.manual_seed(0)
    kwargs['num_inference_steps'] = 50
    kwargs['num_frames'] = 49


def image_to_video(prompt: str, 
                   image: Image, 
                   negative_prompt: str = None,
                   guidance_scale:float = 6.0, 
                   video_filename:str = None, 
                   gif_filename: str = None, 
                   display_video:bool = True, 
                   sequences: int = 1) -> List[Image.Image]:
    # If sequences > 1, we will generate multiple videos and concatenate them, using the last frame from each video to start the next one
    all_frames = []
    for _ in range(sequences):
        video = pipe(prompt=prompt, image=image, guidance_scale=guidance_scale, **kwargs).frames[0]
        all_frames.extend(video)
        # Use last frame as input for next video
        image = video[-1]
    
    if video_filename:
        export_to_video(all_frames, video_filename, fps=8)
        if display_video:
            display(Video(video_filename))
    if gif_filename:
        export_to_gif(all_frames, gif_filename)
        # if display_video:
            # display(Video(gif_filename))
    return all_frames