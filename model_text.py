# import torch
import settings
from model import *

# from typing import Any, Dict, List, Optional, cast

from llama_index_log_handler import callback_manager

from llama_index.core.llms import ChatMessage

from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from typing import List
from IPython.display import Markdown, display


# TODO: Nim


# Temperature of 0 means deterministic output, while 1 means random output
# if settings.TEMPERATURE == 0.0:
#     torch.random.manual_seed(0)

if settings.TEXT_MODEL_BACKEND == "ollama":

    llm = Ollama(
        model=settings.TEXT_MODEL,
        request_timeout=1200.0,
        temperature=settings.TEMPERATURE,
        callback_manager=callback_manager,
    )

    llm_json = Ollama(
        model=settings.TEXT_MODEL,
        request_timeout=1200.0,
        temperature=settings.TEMPERATURE,
        callback_manager=callback_manager,
        json_mode=True,
    )

    embedding = OllamaEmbedding(
        model_name=settings.TEXT_MODEL,
        # base_url="http://localhost:11434",
        ollama_additional_kwargs={"mirostat": 2},
    )

elif settings.TEXT_MODEL_BACKEND == "nim":
    import os
    from llama_index.llms.nvidia import NVIDIA
    from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader
    from llama_index.core.node_parser import SentenceSplitter

    # Configure the NVIDIA LLM to connect to your local NIM server
    llm = NVIDIA(
        model=settings.TEXT_MODEL,
        base_url="http://localhost:8000",  # Adjust if your NIM server uses a different port
        # base_url = "https://integrate.api.nvidia.com/v1",
        api_key = os.environ["NGC_API_KEY"]
    )

    # Set the LLM as the default for LlamaIndex
    Settings.llm = llm


# from llama_index.llm_predictor import LLMPredictor
# from llama_index.prompts.prompts import Prompt
# from llama_index.response.schema import RESPONSE_TYPE
# from typing import Any, Optional

# from nemoguardrails import LLMRails, RailsConfig


def display_messages(messages: List[ChatMessage]):
    if not settings.DEBUG:
        return
    
    output = "---\n\n### Messages\n\n"
    for m in messages:
        output += f"#### {m.role.title()}:\n\n"
        if m.content.startswith("{"):
            try:
                json_content = json.loads(m.content)
                formatted_json = json.dumps(json_content, indent=4)
                output += f"```json\n{formatted_json}\n```\n\n"
            except json.JSONDecodeError:
                output += f"```json\n{m.content}\n```\n\n"
        else:
            output += "\n".join(["> "+  line for line in m.content.split("\n")])
            output += "\n\n"

    output += "\n---\n\n"
    display(Markdown(output))


def stream_llm_response(response, progress=None):
    line_len = 0
    for r in response:
        if progress:
            progress.value += 1
        print(r.delta, end="")
        line_len += len(r.delta)
        if line_len > 120:
            print()
            line_len = 0
        elif "\n" in r.delta:
            line_len = 0
    return r.message.content


# # This is for llama
# generator = pipeline(model=settings.TEXT_MODEL, device_map=settings.DEVICE_MAP, torch_dtype=torch.bfloat16)

# def run_llm(messages: list[dict[str, str]], max_new_tokens: int = 500, temperature: float = settings.TEMPERATURE) -> str:
#     generation = generator(
#         messages,
#         do_sample=temperature > 0,
#         temperature=1.0,
#         top_p=settings.TOP_P if temperature > 0 else 1,
#         max_new_tokens=max_new_tokens,
#         pad_token_id=generator.tokenizer.eos_token_id,
#     )
#     return generation[0]['generated_text'][-1]['content'].strip()


def free_memory():
    """Free memory up after running the text model"""
    pass
    # print("Max mem allocated (GB) while doing text model:", torch.cuda.max_memory_allocated() / (1024**3))

    # from numba import cuda

    # device = cuda.get_current_device()
    # device.reset()

    # # Step 1: Delete all references to the models and pipelines
    # try:
    #     del generator
    # except:
    #     pass

    # # Step 2: Run garbage collection to free up Python memory references
    # gc.collect()

    # # Step 3: Empty the CUDA cache to free memory back to PyTorch
    # torch.cuda.empty_cache()

    # # Step 4 (Optional): Synchronize CUDA to ensure all operations are complete
    # torch.cuda.synchronize()


# TODO: Check for Phi-3.5-mini-instruct vs llama

# # Load the model
# model_text_args = {
#     "device_map": settings.DEVICE_MAP,
#     "torch_dtype": "auto",
#     "trust_remote_code": True,
#     "attn_implementation": settings.ATTN_IMPLEMENTATION,
# }

# model_text = AutoModelForCausalLM.from_pretrained(settings.TEXT_MODEL, **model_text_args)
# tokenizer_text = AutoTokenizer.from_pretrained(settings.TEXT_MODEL)

# pipe_text = pipeline(
#     "text-generation",
#     model=model_text,
#     tokenizer=tokenizer_text,
# )

# Define the function to run text generation
# def run_llm(messages: list[dict[str, str]], max_new_tokens: int = 500, temperature: float = settings.TEMPERATURE) -> str:
#     generation_args = {
#         "max_new_tokens": max_new_tokens,
#         "return_full_text": False,
#         "temperature": temperature,
#         "do_sample": True,
#         "top_p": settings.TOP_P,
#         "pad_token_id": pipe_text.tokenizer.eos_token_id
#     }
#     if temperature == 0.0:
#         generation_args["do_sample"] = False
#         generation_args["temperature"] = None
#         generation_args["top_p"] = None

#     output = pipe_text(messages, **generation_args)
#     return output[0]['generated_text'].strip()

