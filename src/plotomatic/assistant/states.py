class AssistantState:
    GENERATING_OUTPUT = "GENERATING_OUTPUT"           # LLM generating a response
    WAITING_USER_INPUT = "WAITING_USER_INPUT"        # Waiting for user message
    PROCESSING_TOOL_CALLS = "PROCESSING_TOOL_CALLS"  # We have one or more tool calls to execute
    PROCESSING_TOOL_OUTPUTS = "PROCESSING_TOOL_OUTPUTS"  # After tools have executed, re-check LLM with tool outputs
