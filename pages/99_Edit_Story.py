# pages/2_Edit_Story.py

# TODO: Remind user to save before leaving the page

import streamlit as st
from plotomatic.components import project_selector, view_diffs_and_manage_changes
from streamlit_monaco import st_monaco
from project_manager import ProjectManager
from models.story import Story
from models.story_dialogue import StoryDialogue
import json
from plotomatic.components.json_editor_tab import json_editor_tab

def has_changes(original: str, current: str) -> bool:
    """Compare original and current JSON strings to detect changes"""
    if original is None:
        original = ''
    if current is None:
        current = ''
    return original.strip() != current.strip()

def get_project_state_key(project_name: str, key: str) -> str:
    """Create a namespaced session state key for the project"""
    return f"project_{project_name}_{key}"

def get_project_state(project_name: str, key: str, default=None):
    """Get a project-specific session state value"""
    state_key = get_project_state_key(project_name, key)
    return st.session_state.get(state_key, default)

def set_project_state(project_name: str, key: str, value):
    """Set a project-specific session state value"""
    state_key = get_project_state_key(project_name, key)
    st.session_state[state_key] = value

def edit_story():
    st.title("✏️ Edit Raw Story Data")

    # Sidebar
    project_selector()

    if 'current_project' not in st.session_state or not st.session_state.current_project:
        st.error("No project selected. Please select or load a project first.")
        return

    project_name = st.session_state.current_project
    
    # Initialize project-specific session state
    if not get_project_state(project_name, 'original_content'):
        set_project_state(project_name, 'original_content', {
            'story': '',
            'story_dialogue': ''
        })
    if not get_project_state(project_name, 'current_tab'):
        set_project_state(project_name, 'current_tab', 'story')
    if not get_project_state(project_name, 'edited_content'):
        set_project_state(project_name, 'edited_content', {
            'story': '',
            'story_dialogue': ''
        })

    pm = ProjectManager()
    project_path = pm.open_project(project_name)

    if not project_path:
        st.error("Project path not found.")
        return

    # Load story if not loaded for this project
    if not get_project_state(project_name, 'current_story'):
        story = pm.load_story(project_path)
        if story:
            set_project_state(project_name, 'current_story', story)
            # Initialize original content using direct file loading
            set_project_state(project_name, 'original_content', {
                'story': pm.load_json_file(project_path, 'story.json'),
                'story_dialogue': pm.load_json_file(project_path, 'story_dialogue.json')
            })
        else:
            st.error("No story found in the project. Please create a story first.")
            return

    # Get current edit states before creating tabs
    original_content = get_project_state(project_name, 'original_content')
    edited_content = get_project_state(project_name, 'edited_content')
    current_tab = get_project_state(project_name, 'current_tab')

    # Create tabs
    story_tab, dialogue_tab = st.tabs(["📝 story.json", "💭 story_dialogue.json"])

    with story_tab:
        set_project_state(project_name, 'current_tab', 'story')
        json_editor_tab(
            file_name='story.json',
            model_class=Story,
            title='Story Outline',
            description='Edit your story\'s main structure in JSON format',
            project_name=project_name,
            project_manager=pm,
            original_content=original_content,
            edited_content=edited_content,
            set_project_state=set_project_state,
            get_project_state=get_project_state,
            has_changes=has_changes
        )

    with dialogue_tab:
        set_project_state(project_name, 'current_tab', 'dialogue')
        json_editor_tab(
            file_name='story_dialogue.json',
            model_class=StoryDialogue,
            title='Story Dialogue',
            description='Edit your story\'s dialogue and conversations in JSON format',
            project_name=project_name,
            project_manager=pm,
            original_content=original_content,
            edited_content=edited_content,
            set_project_state=set_project_state,
            get_project_state=get_project_state,
            has_changes=has_changes
        )

    view_diffs_and_manage_changes()



if __name__ == "__main__":
    edit_story()
