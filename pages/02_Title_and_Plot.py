# pages/3_Set_Story_Info.py

import streamlit as st
from components import project_selector, view_diffs_and_manage_changes, selected_project_name
from project_manager import ProjectManager, CURRENT_PROJECT_KEY
from model import Story  # Correct import
import json

def generate_plot_overview(title, author):
    """Generate a simple plot overview based on title and author."""
    return f"Plot overview for '{title}': This is a story by {author} about something extraordinary."


def set_story_info():
    st.title("Set Story Info")

    # st.title("Selected Project: " + st.session_state[CURRENT_PROJECT_KEY])
    selected_project_name()

    # Include project selector and diff management at the top
    project_selector()
    view_diffs_and_manage_changes()

    if CURRENT_PROJECT_KEY not in st.session_state or not st.session_state.current_project:
        st.error("No project selected. Please select or load a project first.")
        return

    pm = ProjectManager()
    project_name = st.session_state.current_project
    project_path = pm.open_project(project_name)

    if not project_path:
        st.error("Project path not found.")
        return

    # Load story or create a new one
    if 'current_story' not in st.session_state or st.button("Load Story"):
        story = pm.load_story(project_path)
        if story:
            st.session_state.current_story = story
            st.success(f"Story loaded: {story.title}")
        else:
            st.session_state.current_story = Story()
            st.warning("No existing story found. Starting a new one.")

    story = st.session_state.current_story

    # Form to set title, author, and author email
    with st.form("set_story_info_form"):
        title = st.text_input("Title", value=story.title)
        author = st.text_input("Author", value=story.author)
        author_email = st.text_input("Author Email", value=getattr(story, "author_email", ""))
        
        generate_overview = st.checkbox("Generate Plot Overview", value=False)
        submit = st.form_submit_button("Save Info")

    if submit:
        story.title = title
        story.author = author
        story.author_email = author_email

        if generate_overview:
            story.content = generate_plot_overview(title, author)

        # Save the updated story
        pm.save_story(story, project_path)
        st.success("Story info saved successfully.")
        st.session_state.current_story = story

        view_diffs_and_manage_changes()
    # # View diffs and commit
    # st.write("### Manage Changes")
    # repo = pm.get_repo(project_path)

    # changed_files = repo.index.diff(None)
    # if changed_files:
    #     st.write("Changed files detected:")
    #     for item in changed_files:
    #         st.text(f"- {item.a_path}")
    # else:
    #     st.write("No changes detected.")

    # # Buttons to commit or discard changes
    # col1, col2 = st.columns(2)
    # with col1:
    #     if st.button("Commit Changes"):
    #         repo.index.add([item.a_path for item in changed_files])
    #         repo.index.commit("Updated story info")
    #         st.success("Changes committed.")
    # with col2:
    #     if st.button("Discard Changes"):
    #         repo.git.checkout("--", ".")
    #         st.success("Changes discarded.")

    

if __name__ == "__main__":
    set_story_info()

