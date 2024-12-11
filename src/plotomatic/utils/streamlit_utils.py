import streamlit as st
from plotomatic.utils.story_utils import show_diff

def display_story(story, title="View Story Object", expanded=False):
    json_data = story.model_dump_json(indent=4)
    with st.expander(title, expanded=expanded):
        st.json(json_data)

def display_diff(story1, story2, expanded=True):
    with st.expander("Updated Story", expanded=expanded):
        diff = show_diff(story1, story2, return_diff=True)
        st.markdown(f"```diff\n{diff}\n```")
