"""
NVIDIA NeMo Guardrails loader and writer.
This module provides functionality to read and write JSON schema files for the Story and StoryDialog models.
"""

from model import Story, StoryDialogue
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.actions import action
import json
from pydantic import ValidationError
import time
from typing import Optional
from json_repair import repair_json

import nest_asyncio

# Allow async operation in interactive environments
nest_asyncio.apply()

story_config = None
story_dialog_policy = None

story_config_path = "rails/story/"
story_schema_path = story_config_path + "/story_schema.json"
story_dialog_schema_path = story_config_path + "/story_dialog_schema.json"
# story_dialog_policy_config_path = "rails/story_dialog/"

def write_schema():
    """
    Generates JSON schema files for Story and StoryDialog models.

    This function retrieves the JSON schema for the Story and StoryDialog models
    and writes them to `story_config_path` and `story_dialog_policy_path` files
    respectively.
    """
    # For Story
    story_schema = Story.model_json_schema()
    with open(story_schema_path, 'w') as f:
        json.dump(story_schema, f, indent=2)

    # For StoryDialog
    story_dialog_schema = StoryDialogue.model_json_schema()
    with open(story_dialog_schema_path, 'w') as f:
        json.dump(story_dialog_schema, f, indent=2)

def load_guardrails():
    """
    Loads the yaml configuration files for the Story and StoryDialog models from `story_config_config_path` and `story_dialog_policy_config_path`.
    Inside those, are references to the JSON schema files `story_config_path` and `story_dialog_policy_path`.
    """
    # global story_config, story_dialog_policy
    # story_config = RailsConfig.from_path(story_config_path)
    # story_dialog_policy = RailsConfig.from_path(story_dialog_policy_config_path)
    


def rail_story():
    """Retries if failed to get a JSON response that can be parsed into a Story object"""
    # # load_guardrails()
    # story_config = RailsConfig.from_path(story_config_path)
    # return LLMRails(story_config)

    config = RailsConfig.from_content(
        yaml_content="""
            tracing:
                enabled: true
                
            models:
            - type: main
              engine: ollama
              model: nemotron:70b
              temperature: 0.0

            # Output rails are triggered after a bot message has been generated.
            rails:
                output:
                    flows:
                    - retry json
            
            json_parser:
                retries: 3
        """,
        colang_content="""
            define bot inform cannot parse json
                "Unable to parse the Story JSON."

            # If we can't parse json, we retry
            define subflow retry json
                $failed_json = execute retry_json

                if $failed_json
                    bot inform cannot parse json
                    stop
        """,
    )
    app = LLMRails(config, verbose=True)

    @action(is_system_action=True)
    def retry_json(context: Optional[dict] = None, retries: int=0) -> str:
        from pprint import pprint
        print("!!!!!!!!!! call_llm !!!!!!!!!!!")

        if retries > 3:
            # Failed too many times!
            print("Failed too many times!")
            return True
        
        if retries > 0:
            print(f"Retry {retries}")

        config = app.config
        print(f"config: ")
        pprint(config)
        print(f"retries: {retries}")

        bot_response = context.get("bot_message")
        user_message = context.get("user_message")
        # call_config = RunnableConfig(callbacks=[streaming_handler_var.get()])
        # response = llm.invoke(user_query, config=call_config)
        # return response.content
        
        print(f"bot_response: {bot_response}")
        print(f"user_message: {user_message}")
        # print(f"retries: {retries}")
        
        print("context:")
        pprint(context)

        try:
            story = Story.model_validate_json(bot_response)
            print("story:")
            print(story.model_dump_json(indent=2))
            return False
        # except ValidationError as e:
        except BaseException as e:
            print(f"Failed to parse Story JSON. Trying to repair json. Attempt {retries+1}")
            # Try to fix up the json
            try:
                bot_response = repair_json(bot_response)
                story = Story.model_validate_json(bot_response)
                print("story:")
                print(story.model_dump_json(indent=2))
                print("Successfully repaired JSON")
                return False
            # except ValidationError as e:
            except Exception as e2:
                print(f"Failed to parse Story JSON. Attempt {retries+1}")
                print(e2)
            return retry_json(context, retries=retries+1)
    
    app.register_action(retry_json)

    return app
    

    

# def rail_story_dialog():
#     load_guardrails()
#     return LLMRails(config=story_dialog_policy)


if __name__ == "__main__":
    write_schema()
    rail_story()
