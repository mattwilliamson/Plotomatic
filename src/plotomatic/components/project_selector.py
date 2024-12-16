import streamlit as st
from plotomatic.project_manager import get_project_manager, CURRENT_PROJECT_KEY, PROJECT_LIST_KEY
from streamlit.logger import get_logger

logger = get_logger(__name__)

pm = get_project_manager()

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
            st.toast(f"Switched to project: {selected_project} 📂", icon="🔄")
            
            refresh_projects()
            st.session_state[CURRENT_PROJECT_KEY] = selected_project
            st.rerun()

    # if there is no project selected and there is only one project, select it
    if not current_project and len(st.session_state[PROJECT_LIST_KEY]) == 1:
        pm.open_project(st.session_state[PROJECT_LIST_KEY][0])
        st.toast(f"Loaded project: {st.session_state[PROJECT_LIST_KEY][0]} 📂", icon="✨")
        st.rerun() 