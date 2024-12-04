# pages/2_Edit_Story.py

import streamlit as st
from components import project_selector, view_diffs_and_manage_changes
from streamlit_monaco import st_monaco
from project_manager import ProjectManager
from model import Story  # Corrected import
import json

def edit_story():
    st.title("Edit Story")

    # Include project selector and diff management at the top
    project_selector()
    view_diffs_and_manage_changes()

    if 'current_project' not in st.session_state or not st.session_state.current_project:
        st.error("No project selected. Please select or load a project first.")
        return

    pm = ProjectManager()
    project_name = st.session_state.current_project
    project_path = pm.open_project(project_name)

    if not project_path:
        st.error("Project path not found.")
        return

    # Add a "Load Story" button to explicitly load the story
    if 'current_story' not in st.session_state or st.button("Load Story"):
        story = pm.load_story(project_path)
        if story:
            st.session_state.current_story = story
            st.success(f"Story loaded: {story.title}")
        else:
            st.error("No story found in the project. Please create a story first.")
            return

    # Display the story data in a Monaco editor
    if 'current_story' in st.session_state:
        story = st.session_state.current_story
        story_json_str = story.json(indent=4)
        edited_story_json_str = st_monaco(value=story_json_str, language='json', height=400)

        # Save button
        if st.button("Save Story"):
            try:
                # Parse the edited JSON
                edited_story_data = json.loads(edited_story_json_str)
                # Create a Story object to validate data
                edited_story = Story(**edited_story_data)
                # Save the story
                pm.save_story(edited_story, project_path)
                st.success("Story saved successfully.")
                # Update session state
                st.session_state.current_story = edited_story
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
            except Exception as e:
                st.error(f"Error saving story: {e}")

if __name__ == "__main__":
    edit_story()
