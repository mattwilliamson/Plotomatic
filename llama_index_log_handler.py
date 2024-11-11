"""The callback_manager in this file will log all interactions with the LLM model to the console. This is useful for debugging purposes. """

import settings
import logging

from typing import Any, Dict, List, Optional, cast
from llama_index.core.callbacks.pythonically_printing_base_handler import (
    PythonicallyPrintingBaseHandler,
)
from llama_index.core.callbacks.schema import CBEventType, EventPayload

from llama_index.core.callbacks import (
    CallbackManager,
    LlamaDebugHandler,
    CBEventType,
)

from llama_index.core.llms import ChatMessage

import time


# Initialize logger
logger = logging.getLogger('llama_index_log_handler')
ch = logging.StreamHandler()
formatter = logging.Formatter('## LLM ## %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def set_log_level(level: int) -> None:
    logger.setLevel(level)
    ch.setLevel(level)

set_log_level(logging.DEBUG)

def enable() -> None:
    """
    Enables the log handler by setting the 'enabled' attribute to True.

    This function modifies the global state of the log handler, allowing it to start processing and logging messages.
    """
    log_handler.enabled = True

def disable() -> None:
    """
    Disables the log handler by setting its 'enabled' attribute to False.

    This function modifies the global state of the log handler, effectively
    turning off any logging that would be handled by it.
    """
    log_handler.enabled = False


class LogHandler(PythonicallyPrintingBaseHandler):
    """A simple handler for LLM events that prints the prompt and completion for every inference. For debugging."""

    def __init__(self, logger: Optional[logging.Logger] = logger) -> None:
        super().__init__(
            event_starts_to_ignore=[], event_ends_to_ignore=[], logger=logger
        )
        self._start_times: Dict[str, float] = {}
        self.enabled = True

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        if trace_id is not None:
            self._start_times[trace_id] = time.time()

    def end_trace(
        self,
        trace_id: Optional[str] = None,
        trace_map: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        if trace_id is not None and trace_id in self._start_times:
            start_time = self._start_times.pop(trace_id)
            elapsed_time = time.time() - start_time
            self._print(f"Trace {trace_id} took {elapsed_time:.2f} seconds")
    
    def _print(self, *args, **kwargs) -> None:
        if not self.enabled:
            return
        super()._print(*args, **kwargs)

    def _print_llm_event(self, payload: dict) -> None:
        if EventPayload.PROMPT in payload:
            prompt = str(payload.get(EventPayload.PROMPT))
            completion = str(payload.get(EventPayload.COMPLETION))

            self._print(f"** Prompt: **\n{prompt}")
            self._print("*" * 50)
            self._print(f"** Completion: **\n{completion}")
            self._print("*" * 50)
            self._print("\n")
        elif EventPayload.MESSAGES in payload:
            messages = cast(List[ChatMessage], payload.get(EventPayload.MESSAGES, []))
            messages_str = "\n".join([str(x) for x in messages])
            response = str(payload.get(EventPayload.RESPONSE))

            self._print("*" * 50)
            self._print(f"** Messages: **\n{messages_str}")
            self._print("*" * 50)
            self._print(f"** Response: **\n{response}")
            self._print("*" * 50)
            self._print("\n")

        if "response" in payload:
            chat_response = payload['response']
            raw = chat_response.raw
            model = raw.get('model', "")
            total_duration = raw.get('total_duration', 0.) / 1e9
            
            if 'usage' in raw:
                usage = raw['usage']
                prompt_tokens, completion_tokens, total_tokens = usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0), usage.get('total_tokens', 0)
                self._print('#'*50)
                self._print(f"##### Got LLM Response from model: {model}, total_duration: {total_duration:.2f}s, prompt_tokens: {prompt_tokens}, completion_tokens: {completion_tokens}, total_tokens: {total_tokens}")

    def on_event_start(
        self,
        event_type: CBEventType,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        self._print("-" * 50)
        self._print(f"Event {event_type} started")
        self._print("-" * 50)
        return event_id

    def on_event_end(
        self,
        event_type: CBEventType,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        """Count the LLM or Embedding tokens as needed."""
        self._print("-" * 50)
        self._print(f"Event {event_type} ended")
        if event_type == CBEventType.LLM and payload is not None:
            self._print_llm_event(payload)
        self._print("-" * 50)



log_handler = LogHandler(logger)
callback_manager = CallbackManager([log_handler])

if settings.DEBUG:
    enable()
else:
    disable()