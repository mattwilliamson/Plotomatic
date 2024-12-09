# project_manager.py

import os
import json
from pathlib import Path
from models.story import Story
from models.chat import ChatSession
from typing import Optional
from plotomatic.git_utils import create_repo, add_file, commit_changes
import streamlit as st

SESSION_FILE = "session_settings.json"
CURRENT_PROJECT_KEY = 'current_project'
PROJECT_LIST_KEY = 'project_list'

class ProjectManager:
    def __init__(self, stories_dir='stories'):
        self.root_dir = Path(__file__).resolve().parent  # Resolve to the script's root directory
        self.stories_dir = self.root_dir / stories_dir
        self.stories_dir.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
        self.session_file = self.stories_dir / SESSION_FILE
        self._load_session()

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

    def create_project(self, project_name: str):
        """Create a new project directory and initialize it."""
        project_path = self.stories_dir / project_name
        if not project_path.exists():
            project_path.mkdir(parents=True, exist_ok=True)
            repo = create_repo(project_path)
            Story().save_to_directory(project_path)  # Create an empty story
            add_file(repo, 'story.json')
            add_file(repo, 'story_dialogue.json')
            commit_changes(repo, "Initial commit: Add empty story")
            return True
        return False

    def open_project(self, project_name: str):
        """Set the current project in session settings."""
        if project_name in self.get_projects():
            self.session_settings[CURRENT_PROJECT_KEY] = project_name
            self._save_session()
            return project_name
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
            return ChatSession(project=self.get_current_project())
        chat_file = project_path / f"chat_{chat_name}.json"
        session = ChatSession.load_from_file(chat_file)
        if session is None:
            session = ChatSession(project=self.get_current_project())
        return session

    def save_chat(self, chat_name: str, chat_session: ChatSession):
        """Save a chat session by name to the current project."""
        project_path = self.get_current_project_path()
        if not project_path:
            raise ValueError("No project loaded. Cannot save chat.")
        chat_file = project_path / f"chat_{chat_name}.json"
        chat_session.save_to_file(chat_file)

    def clear_chat(self, chat_name: str):
        """Clear the chat session by name."""
        project_path = self.get_current_project_path()
        if not project_path:
            return
        chat_file = project_path / f"chat_{chat_name}.json"
        if chat_file.exists():
            chat_file.unlink()  # remove the file
