class AssistantState:
    GENERATING_OUTPUT = 0          # LLM generating a response
    WAITING_USER_INPUT = 1         # Waiting for user message
    PROCESSING_TOOL_CALLS = 2      # We have one or more tool calls to execute
    PROCESSING_TOOL_OUTPUTS = 3    # After tools have executed, re-check LLM with tool outputs
