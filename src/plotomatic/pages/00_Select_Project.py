import streamlit as st
from plotomatic.components import project_selector, view_diffs_and_manage_changes, selected_project_name
from plotomatic.project_manager import get_project_manager, PROJECT_LIST_KEY, CURRENT_PROJECT_KEY
from streamlit_extras.switch_page_button import switch_page


pm = get_project_manager()

def refresh_projects():
    st.session_state[PROJECT_LIST_KEY] = pm.get_projects()

def set_project(new_project_name):
    st.session_state[CURRENT_PROJECT_KEY] = new_project_name

def start_project():
    with st.container():
        selected_project_name()

        st.title("Start a New Project")
        project_selector()

        with st.form("create_project_form"):
            new_project_name = st.text_input("Enter New Project Name")

            if st.form_submit_button("Create New Project"):
                if new_project_name:
                    success = pm.create_project(new_project_name)
                    if success:
                        st.toast(f"Created new project: {new_project_name} 🎉", icon="✨")
                        st.success(f"New project '{new_project_name}' created.")
                        pm.open_project(new_project_name)
                        set_project(new_project_name)
                        print(new_project_name)
                        switch_page("start story")
                        st.rerun()
                    else:
                        st.toast(f"Project '{new_project_name}' already exists", icon="⚠️")
                        st.error(f"Project '{new_project_name}' already exists.")
                else:
                    st.toast("Please enter a project name", icon="❗")
                    st.error("Please enter a project name.")

        # Include project selector and diff management
        
        # view_diffs_and_manage_changes()

if __name__ == "__main__":
    start_project()
