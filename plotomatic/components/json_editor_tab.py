import streamlit as st
from streamlit_monaco import st_monaco
from typing import Type, Optional
from pydantic import BaseModel
from utils import blank_story, blank_story_dialog

def json_editor_tab(
    file_name: str,
    model_class: Type[BaseModel],
    title: str,
    description: str,
    project_name: str,
    project_manager,
    original_content: dict,
    edited_content: dict,
    set_project_state,
    get_project_state,
    has_changes
) -> None:
    """
    Renders a JSON editor tab with save and download functionality
    
    Args:
        file_name: Name of the JSON file (e.g. 'story.json')
        model_class: Pydantic model class for validation
        title: Tab title
        description: Description shown above the editor
        project_name: Current project name
        project_manager: ProjectManager instance
        original_content: Dict containing original file contents
        edited_content: Dict containing edited file contents
        set_project_state: Function to set project state
        get_project_state: Function to get project state
        has_changes: Function to check for changes
    """
    
    base_key = file_name.replace('.json', '')
    
    st.markdown(f"""
    ### 📝 {title}
    
    {description}
    """)
    
    edited_content[base_key] = st_monaco(
        value=original_content[base_key],
        language='json',
        height='600px',
        minimap=True
    )
    set_project_state(project_name, 'edited_content', edited_content)
    
    # Save and Download buttons
    col1, _, col2 = st.columns([2, 1, 2])
    with col1:
        save_disabled = not has_changes(
            original_content[base_key], 
            edited_content[base_key]
        )
        if st.button(f"💾 Save {title}", disabled=save_disabled):
            try:
                # Validate and format the JSON
                obj = model_class.model_validate_json(edited_content[base_key])
                formatted_json = obj.model_dump_json(indent=2)
                
                # Save the formatted JSON
                if file_name == 'story.json':
                    project_manager.save_story(obj, project_manager.current_project_path)
                    set_project_state(project_name, 'current_story', obj)
                else:
                    # TODO: Make sure this dialog gets set to the session state
                    project_manager.save_json_file(
                        project_manager.current_project_path, 
                        file_name, 
                        formatted_json
                    )
                
                original_content[base_key] = formatted_json
                set_project_state(project_name, 'original_content', original_content)
                st.success(f"{title} saved successfully.")
                
                # Reload story if needed
                if file_name == 'story_dialogue.json':
                    story = project_manager.load_story(project_manager.current_project_path)
                    set_project_state(project_name, 'current_story', story)
                
                st.rerun()
            except Exception as e:
                st.exception(e)
    
    with col2:
        if edited_content[base_key]:
            st.download_button(
                label=f"⬇️ Download {title}",
                data=edited_content[base_key],
                file_name=file_name,
                mime="application/json",
            )

    # Schema viewer
    with st.expander(f"❓ View Data Schema"):
        schema = model_class.schema_markdown()
        st.markdown(schema) 
        
    # Add example JSON viewer
    with st.expander(f"📋 View Example JSON"):
        example = blank_story if file_name == 'story.json' else blank_story_dialog
        example_json = example.model_dump_json(indent=2)
        st.code(example_json, language='json') 