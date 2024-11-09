import settings

# Phi-3.5-vision
from PIL import Image 
import requests 
import torch
from transformers import AutoProcessor 
from typing import Union, List


model_id = settings.VISION_MODEL
device_map = settings.VISION_DEVICE_MAP

if "Phi-3.5-vision" in model_id:
    from transformers import AutoModelForCausalLM 

    # Note: set _attn_implementation='eager' if you don't have flash_attn installed
    model = AutoModelForCausalLM.from_pretrained(
    model_id, 
    #   device_map="cuda", 
    device_map=device_map, 
    trust_remote_code=True, 
    torch_dtype="auto", 
    _attn_implementation='flash_attention_2'    
    )

    # for best performance, use num_crops=4 for multi-frame, num_crops=16 for single-frame.
    processor = AutoProcessor.from_pretrained(model_id, 
        trust_remote_code=True, 
        num_crops=4
    ) 
elif "meta-llama/Llama-3.2" in model_id:
    from transformers import MllamaForConditionalGeneration

    model = MllamaForConditionalGeneration.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map=device_map,
    )
    processor = AutoProcessor.from_pretrained(model_id)


def vision_prompt(prompt_images: Union[Image.Image, List[Image.Image]], prompt_text: str, max_tokens: int=1000):
    images = []
    placeholder = ""

    if isinstance(prompt_images, list):
        images = prompt_images
    else:
        images = [prompt_images]

    # Transformers

    # Phi-3.5-vision transformers
    if "Phi-3.5-vision" in model_id:
        # Note: if OOM, you might consider reduce number of frames in this example.
        for i, _ in enumerate(images):
            placeholder += f"<|image_{i+1}|>\n"

        # Convert to list for consistent handling
        images = [image for image in images]

        messages = [
            {"role": "user", "content": placeholder + prompt_text},
        ]

        prompt = processor.tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
        )

        inputs = processor(prompt, images, return_tensors="pt").to("cuda:0") 

        generation_args = { 
            "max_new_tokens": max_tokens, 
            "temperature": 0.0, 
            "do_sample": False, 
        } 

        generate_ids = model.generate(**inputs, 
            eos_token_id=processor.tokenizer.eos_token_id, 
            **generation_args
        )

        # remove input tokens 
        generate_ids = generate_ids[:, inputs['input_ids'].shape[1]:]
        response = processor.batch_decode(generate_ids, 
        skip_special_tokens=True, 
        clean_up_tokenization_spaces=False)[0] 

    # Llama3.2 transformers
    elif "meta-llama/Llama-3.2" in model_id:
        prompt = "<|image|><|begin_of_text|>" + prompt_text
        inputs = processor(prompt_images[0], prompt, return_tensors="pt").to(model.device)

        output = model.generate(**inputs, max_new_tokens=max_tokens)

        return processor.decode(output[0])


    return response
