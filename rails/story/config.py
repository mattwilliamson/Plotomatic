# https://github.com/NVIDIA/NeMo-Guardrails/blob/develop/docs/user_guides/configuration-guide.md

from model import Story
from nemoguardrails import LLMRails
from json_repair import json_repair
from guardrails import action
from pydantic import ValidationError

# def init(app: LLMRails):
#     # Initialize the database connection
#     db = ...

#     # Register the action parameter
#     app.register_action_param("db", db)

@action()
async def validate_story(output: str) -> str:
    try:
        # Attempt to parse the output into the Story model
        story = Story.model_validate_json(output)

        # Return the validated JSON if successful
        return story.model_dump_json(indent=4)  
    except ValidationError as e:
        # Maybe it's json but a little messed up
        fixed_output = json_repair(output)

        try:
            # Attempt to parse the output into the Story model
            story = Story.model_validate_json(fixed_output)

            # Return the validated JSON if successful
            return story.model_dump_json(indent=4)
        except ValidationError as e:
            # TODO: Retry the LLM
            return f"Validation error: {e.errors()}"