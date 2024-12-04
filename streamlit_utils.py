import streamlit as st
from model import Story
from utils import deindent, show_diff, merge_models, get_step_directory
# from model_text import llm_json, display_messages
# import settings

def display_story(story, title="View Story Object", expanded=False):
    json_data = story.model_dump_json(indent=4)
    with st.expander(title, expanded=expanded):
        st.json(json_data)

def display_diff(story1, story2, expanded=True):
    with st.expander("Updated Story", expanded=expanded):
        diff = show_diff(story1, story2, return_diff=True)
        st.markdown(f"```diff\n{diff}\n```")
