# pages/3_View_Diffs.py

import streamlit as st
import os
from project_manager import get_project_manager
from plotomatic.utils.git_utils import get_repo, get_changed_files, get_diff, commit_changes, discard_changes

def view_diffs():
    st.title("View Diffs")

    if 'current_project' not in st.session_state or not st.session_state.current_project:
        st.error("No project selected. Please select or create a project first.")
        return

    pm = get_project_manager()
    # project_name = st.session_state.current_project
    # project_path = pm.open_project(project_name)
    project_path = pm.get_current_project_path()

    if not project_path:
        st.error("Project path not found.")
        return

    repo = get_repo(project_path)

    changed_files = get_changed_files(repo)

    if changed_files:
        st.write("Changed files:")
        selected_file = st.selectbox("Select a file to view diff", changed_files)
        if selected_file:
            diff_text = get_diff(repo, selected_file)
            if diff_text:
                st.code(diff_text, language='diff')
            else:
                st.write("No differences found.")
    else:
        st.write("No uncommitted changes.")

    commit_message = st.text_input("Commit Message", value="Updated files")

    if st.button("Commit Changes"):
        if commit_message:
            commit_changes(repo, commit_message)
            st.success("Changes committed.")
        else:
            st.error("Please enter a commit message.")

    if st.button("Discard Changes"):
        discard_changes(repo)
        st.success("Changes discarded.")

if __name__ == "__main__":
    view_diffs()
