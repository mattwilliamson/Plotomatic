import os

# Story directory path - defaults to "stories" if not set in environment
STORY_DIR = os.getenv("STORY_DIR", "stories")

# Debug mode - defaults to False if not set in environment
# Convert string 'true'/'false' to boolean
# DEBUG = os.getenv("DEBUG", "false").lower() == "true" 
DEBUG = os.getenv("DEBUG", "true").lower() == "true" 