# components.py

import streamlit as st
from project_manager import ProjectManager, CURRENT_PROJECT_KEY, PROJECT_LIST_KEY
from git_utils import get_repo, get_changed_files, get_diff, commit_changes, discard_changes
from git import InvalidGitRepositoryError


pm = ProjectManager()

def selected_project_name():
    if CURRENT_PROJECT_KEY not in st.session_state:
        st.session_state[CURRENT_PROJECT_KEY] = pm.get_current_project()

    current_project = st.session_state[CURRENT_PROJECT_KEY]

    if current_project:
        st.sidebar.markdown(f"## Selected Project: `{current_project}`")

def project_selector():
    """Display a dropdown to select a project and update session state."""
    def refresh_projects():
        st.session_state[PROJECT_LIST_KEY] = pm.get_projects()

    refresh_projects()

    if CURRENT_PROJECT_KEY not in st.session_state:
        st.session_state[CURRENT_PROJECT_KEY] = pm.get_current_project()

    current_project = st.session_state[CURRENT_PROJECT_KEY]

    with st.sidebar.form("load_project_form"):
        selected_project = st.selectbox(
            "Select a Project",
            st.session_state[PROJECT_LIST_KEY],
            index=st.session_state[PROJECT_LIST_KEY].index(current_project) if current_project in st.session_state[PROJECT_LIST_KEY] else 0
        )

        if st.form_submit_button("Load Selected Project"):
            pm.open_project(selected_project)
            st.success(f"Loaded project: {selected_project}")
            refresh_projects()
            st.session_state[CURRENT_PROJECT_KEY] = selected_project
            st.rerun()

def render_view_diffs_and_manage_changes():
    st.session_state.view_diffs_and_manage_changes = True

def view_diffs_and_manage_changes():
    """Reusable diff viewer and change management controls."""
    if 'view_diffs_and_manage_changes' not in st.session_state:
        st.session_state.view_diffs_and_manage_changes = False

    if CURRENT_PROJECT_KEY not in st.session_state:
        st.session_state[CURRENT_PROJECT_KEY] = pm.get_current_project()

    current_project = st.session_state[CURRENT_PROJECT_KEY]

    if not current_project:
        st.error("No project selected. Please select or create a project first.")
        return

    project_path = pm.get_current_project_path()

    if not project_path:
        st.error("Project path not found.")
        return

    try:
        repo = get_repo(project_path)
    except (InvalidGitRepositoryError, FileNotFoundError) as e:
        st.error(f"Invalid Git repository: {e}")
        return
    
    st.session_state.changed_files = get_changed_files(repo)

    if st.session_state.changed_files:
        st.session_state.view_diffs_and_manage_changes = True
    else:
        st.write("No changes detected.")
        st.session_state.changed_files = None

    if st.session_state.view_diffs_and_manage_changes:
        with st.form("diffs_and_changes_form"):
            if st.session_state.changed_files:
                with st.expander("Diffs", expanded=True):
                    st.write("Changed files:")
                    selected_file = st.selectbox("Select a file to view diff", st.session_state.changed_files, key="diff_select")
                    if selected_file:
                        diff_text = get_diff(repo, selected_file)
                        if diff_text:
                            st.code(diff_text, language='diff')
                        else:
                            st.write("No differences found.")
            else:
                st.write("No differences found.")

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.form_submit_button("Commit Changes"):
                    commit_changes(repo, "Updated files")
                    st.success("Changes committed.")
                    st.session_state.view_diffs_and_manage_changes = False
                    st.session_state.changed_files = get_changed_files(repo)
                    st.rerun()
            with col2:
                if st.form_submit_button("Discard Changes"):
                    discard_changes(repo)
                    st.success("Changes discarded.")
                    st.session_state.view_diffs_and_manage_changes = False
                    st.session_state.changed_files = get_changed_files(repo)
                    st.rerun()

            with col3:
                st.text(" ")
