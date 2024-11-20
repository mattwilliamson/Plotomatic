from typing import List, Generator, Optional

# import torch
import settings
from model import *

from llama_index_log_handler import callback_manager
from llama_index.core.llms import ChatMessage
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.constants import DEFAULT_CONTEXT_WINDOW

from IPython.display import Markdown, display, clear_output
import ipywidgets as widgets

# TODO: Nim


# Temperature of 0 means deterministic output, while 1 means random output
# if settings.TEMPERATURE == 0.0:
#     torch.random.manual_seed(0)

if settings.TEXT_MODEL_BACKEND == "ollama":

    # Make a custom Ollama model to increase the token limit
    # import ollama
    # from utils import deindent

    # writer_model = 'nemotron'
    # writer_model = 'nemotron:70b'
    # writer_model = 'mistral-large' # 123b

    # modelfile = deindent(f'''
    #     FROM {writer_model}
    #     PARAMETER num_ctx 126000
    #     PARAMETER num_predict 64000
    #     SYSTEM You are an exceptionally talented award-winning author who writes one full-length chapter for a given story outline. You do not write titles, descriptions, settings or think out loud. You only output the narrative text of the chapter.
    # ''')
    # writer_model_tag = f'author-long:{writer_model}'

    # ollama.create(model=writer_model_tag, modelfile=modelfile)

    # Mirostat acts as a "creativity control" for the model's responses. It helps balance between generating coherent, focused text and allowing for more diverse or exploratory outputs.
    # Mirostat can be configured using three main parameters:
    
    # mirostat: This enables or disables the mirostat sampling.
    #     0: Disabled (default)
    #     1: Mirostat
    #     2: Mirostat 2.0 (an enhanced version)
    # mirostat_tau: Controls the balance between coherence and diversity.
    #     Lower values (e.g., 3.0) result in more focused and coherent text.
    #     Higher values allow for more diverse outputs.
    #     Default value: 5.0
    # mirostat_eta: Influences how quickly the algorithm responds to feedback from the generated text.
    #     Lower values lead to slower adjustments.
    #     Higher values make the algorithm more responsive.
    #     Default value: 0.1




    llm = Ollama(
        model=settings.TEXT_MODEL,
        request_timeout=12000.0,
        temperature=settings.TEMPERATURE,
        callback_manager=callback_manager,
        context_window=DEFAULT_CONTEXT_WINDOW * 2,
        keep_alive='48h',
        additional_kwargs={
            "num_predict": 4000,
            "mirostat": 2
        },
    )

    llm_json = Ollama(
        model=settings.TEXT_MODEL,
        request_timeout=12000.0,
        temperature=settings.TEMPERATURE,
        callback_manager=callback_manager,
        json_mode=True,
        context_window=DEFAULT_CONTEXT_WINDOW * 2,
        additional_kwargs={"num_predict": 4000},
        keep_alive='48h',
    )

    embedding = OllamaEmbedding(
        model_name=settings.TEXT_MODEL,
        # base_url="http://localhost:11434",
        ollama_additional_kwargs={"mirostat": 2},
    )

    llm_writer = Ollama(
        # model=settings.TEXT_MODEL,
        # model=writer_model_tag,
        # model='mistral-large',
        model=settings.TEXT_MODEL,
        request_timeout=12000.0,
        temperature=settings.TEMPERATURE,
        callback_manager=callback_manager,
        context_window=40000,
        keep_alive='48h',
        additional_kwargs={
            "num_predict": 10000,
            "mirostat": 2
        },
    )

    llm_reviewer = llm_writer

    # llm_reviewer = Ollama(
    #     # model=settings.TEXT_MODEL,
    #     # model=writer_model_tag,
    #     # model='mistral-large',
    #     model=settings.TEXT_MODEL_REVIEWER,
    #     request_timeout=12000.0,
    #     temperature=settings.TEMPERATURE,
    #     callback_manager=callback_manager,
    #     context_window=40000,
    #     keep_alive='48h',
    #     additional_kwargs={
    #         "num_predict": 1000,
    #         "mirostat": 2
    #     },
    # )

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
        api_key = os.environ["NGC_API_KEY"],
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


def incremental_pretty_print(json_str):
    """Attempt to pretty print incomplete JSON with approximate indentation."""
    indent_level = 0
    formatted_lines = []
    tokens = json_str.splitlines(keepends=True)  # Split into lines for better control

    for line in tokens:
        # Process each character in the line
        temp_line = ""
        for char in line:
            if char in "{[":
                # Opening brace/bracket increases indent level
                temp_line += char
                indent_level += 1
                temp_line += "\n" + "    " * indent_level  # Add new line and indent
            elif char in "]}":
                # Closing brace/bracket decreases indent level
                temp_line += "\n" + "    " * (indent_level - 1) + char
                indent_level = max(0, indent_level - 1)  # Avoid negative indent
            elif char == ",":
                # Commas add a newline at the current indentation level
                temp_line += char + "\n" + "    " * indent_level
            else:
                temp_line += char
        formatted_lines.append(temp_line)

    return "".join(formatted_lines)

def stream_llm_response(
    response: Generator, 
    progress: Optional[widgets.IntProgress] = None, 
    json_mode: bool = True
) -> str:
    """
    Stream LLM response and optionally pretty print JSON.

    Args:
        response (Generator): A generator yielding streamed chunks from the LLM.
        progress (Optional[widgets.IntProgress]): A progress bar widget for tracking progress.
        json_mode (bool): If True, assumes the response is JSON and formats it incrementally.

    Returns:
        str: The complete streamed content (JSON or plain text).
    """
    content_str = ""  # Used for either JSON or plain text

    # Initialize the progress bar and JSON output
    display_handle = display(Markdown("Streaming response..."), display_id=True)

    for r in response:
        # Append the streamed chunk
        content_str += r.delta

        # Update progress bar if provided
        if progress:
            progress.value += len(r.delta.split())
            progress.value = min(progress.value, progress.max)
            progress.description = f"{progress.value} words"

        # Perform JSON formatting if json_mode is enabled
        if json_mode:
            try:
                formatted_content = incremental_pretty_print(content_str)
                content_type = "json"
            except Exception:
                formatted_content = content_str
                content_type = "text"
        else:
            formatted_content = content_str
            content_type = "text"

        # Update the Markdown cell without clearing the progress bar
        display_handle.update(Markdown(f"```{content_type}\n{formatted_content}\n```"))

    # Finalize the display
    if json_mode:
        try:
            parsed_json = json.loads(content_str)
            formatted_content = json.dumps(parsed_json, indent=4)
            display_handle.update(Markdown(f"```json\n{formatted_content}\n```"))
        except json.JSONDecodeError:
            display_handle.update(Markdown("Invalid JSON received."))

    return unidecode(content_str).strip()

def stream_llm_completion(response, progress=None, progress_overall=None):
    line_len = 0
    for r in response:
        if progress:
            progress.value += len(r.delta.split())
            progress.description = f"{progress.value} words"
        if progress_overall:
            progress_overall.value += len(r.delta.split())
        print(r.delta, end="")
        line_len += len(r.delta)
        if line_len > 120:
            print()
            line_len = 0
        elif "\n" in r.delta:
            line_len = 0

    if 'usage' in r.raw:
        print(f"\n\nToken usage: {r.raw['usage']}")

    return unidecode(r.text).strip()


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

