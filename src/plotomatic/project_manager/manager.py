# project_manager.py

import os
import json
from pathlib import Path
from plotomatic.models.story import Story
from plotomatic.models.chat import ChatSession
from typing import Optional
from plotomatic.utils.git_utils import create_repo, add_file, commit_changes
import streamlit as st
from streamlit.logger import get_logger
from plotomatic.config.settings import STORY_DIR

logger = get_logger(__name__)

_global_project_manager = None

def get_project_manager(stories_dir=None) -> 'ProjectManager':
    """Get or create the global ProjectManager instance.
    
    Args:
        stories_dir: Optional override for stories directory. If None, uses STORY_DIR from config.
    
    Returns:
        ProjectManager: The global ProjectManager instance
    """
    global _global_project_manager
    if _global_project_manager is None:
        stories_dir = stories_dir or STORY_DIR
        _global_project_manager = ProjectManager(stories_dir=stories_dir)
    return _global_project_manager

SESSION_FILE = "session_settings.json"
CURRENT_PROJECT_KEY = 'current_project'
PROJECT_LIST_KEY = 'project_list'

class ProjectManager:
    def __init__(self, stories_dir):
        """Initialize ProjectManager with stories directory.
        
        Args:
            stories_dir: Path or string pointing to stories directory
        """
        self.stories_dir = Path(stories_dir)
        self.stories_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.stories_dir / SESSION_FILE

        logger.info(f"ProjectManager initialized with stories_dir: {self.stories_dir}")

        self._load_session()
        if 'author_source' not in self.session_settings:
            self.session_settings['author_source'] = None
            self._save_session()

    def _load_session(self):
        """Load session settings from the session file."""
        if self.session_file.exists():
            with open(self.session_file, 'r') as f:
                self.session_settings = json.load(f)
        else:
            self.session_settings = {CURRENT_PROJECT_KEY: None}

    def _save_session(self):
        """Save session settings to the session file."""
        with open(self.session_file, 'w') as f:
            json.dump(self.session_settings, f, indent=4)

    def get_projects(self):
        """List all projects in the stories directory."""
        projects = [f.name for f in self.stories_dir.iterdir() if f.is_dir()]
        st.session_state[PROJECT_LIST_KEY] = projects
        return projects

    def create_project(self, project_name: str) -> bool:
        """Create a new project directory and initialize it.
        
        Args:
            project_name: The name of the project to create
            
        Returns:
            bool: True if the project was created, False if it already existed
        """
        project_path = self.stories_dir / project_name

        # Switch to the new project
        self.session_settings[CURRENT_PROJECT_KEY] = project_name
        self._save_session()

        if project_path.exists():
            return False
        
        project_path.mkdir(parents=True, exist_ok=True)
        repo = create_repo(project_path)
        story = Story()
        story.get_story_dialogue() # Create empty story dialogue
        story.save_to_directory(project_path)  # Create an empty story
        add_file(repo, 'story.json')
        add_file(repo, 'story_dialogue.json')
        commit_changes(repo, "Initial commit: Add empty story")

        return True

    def open_project(self, project_name: str) -> Optional[Path]:
        """Set the current project in session settings and return project path."""
        if project_name in self.get_projects():
            self.session_settings[CURRENT_PROJECT_KEY] = project_name
            self._save_session()
            return self.stories_dir / project_name  # Return Path object
        return None

    def get_current_project(self) -> Optional[str]:
        """Get the currently loaded project."""
        return self.session_settings.get(CURRENT_PROJECT_KEY)
    
    def get_current_project_path(self) -> Optional[Path]:
        """Get the path to the currently loaded project."""
        project_name = self.get_current_project()
        if project_name:
            return self.stories_dir / project_name
        return None

    def load_story(self, project_name: Optional[str] = None) -> Optional[Story]:
        """Load a story from the specified or current project."""
        project_name = project_name or self.get_current_project()
        if not project_name:
            return None
        project_path = self.get_current_project_path()
        return Story.load_from_directory(project_path)

    def save_story(self, story: Story, project_name: Optional[str] = None):
        """Save a story to the specified or current project."""
        project_name = project_name or self.get_current_project()
        if not project_name:
            raise ValueError("No project specified or loaded.")
        project_path = self.get_current_project_path()
        story.save_to_directory(project_path)
        return project_path

    def load_chat(self, chat_name: str) -> ChatSession:
        """Load a chat session by name from the current project."""
        project_path = self.get_current_project_path()
        if not project_path:
            return ChatSession(project=self.get_current_project() or "")
        chat_file = project_path / f"chat_{chat_name}.json"
        if chat_file.exists():
            with open(chat_file, 'r') as f:
                data = json.load(f)
                return ChatSession(**data)
        return ChatSession(project=self.get_current_project() or "")

    def save_chat(self, chat_name: str, chat_session: ChatSession):
        """Save a chat session by name to the current project."""
        project_path = self.get_current_project_path()
        if not project_path:
            raise ValueError("No project loaded. Cannot save chat.")
        chat_file = project_path / f"chat_{chat_name}.json"
        with open(chat_file, 'w') as f:
            json.dump(chat_session.model_dump(), f, indent=4)

    def clear_chat(self, chat_name: str):
        """Clear the chat session by name."""
        project_path = self.get_current_project_path()
        if not project_path:
            return
        chat_file = project_path / f"chat_{chat_name}.json"
        if chat_file.exists():
            chat_file.unlink()  # remove the file

    def set_author_source(self, source: str):
        """Store the source of the author information."""
        self.session_settings['author_source'] = source
        self._save_session()

    def get_author_source(self) -> Optional[str]:
        """Get the stored author information source."""
        return self.session_settings.get('author_source')

    def load_json_file(self, project_path: Path, filename: str) -> str:
        """Load a JSON file and return its contents as a formatted string.
        
        Args:
            project_path: Path to the project directory
            filename: Name of the JSON file to load
            
        Returns:
            str: Formatted JSON string, or empty string if file doesn't exist
        """
        file_path = project_path / filename
        if not file_path.exists():
            return '{}'
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return json.dumps(data, indent=4)
        except Exception as e:
            st.error(f"Error loading {filename}: {e}")
            return '{}'

    def save_json_file(self, project_path: Path, filename: str, content: str) -> bool:
        """Save a JSON string to a file.
        
        Args:
            project_path: Path to the project directory
            filename: Name of the JSON file to save
            content: JSON string to save
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        file_path = project_path / filename
        try:
            # Validate JSON before saving
            json.loads(content)  # This will raise an exception if invalid
            with open(file_path, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            st.error(f"Error saving {filename}: {e}")
            return False
