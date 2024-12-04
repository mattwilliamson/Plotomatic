import streamlit as st
import json
import os
from pathlib import Path
from model import Story
import settings
from utils import deindent, get_step_directory
import getpass
import subprocess
from streamlit_utils import display_story, display_diff
from components import project_selector, view_diffs_and_manage_changes, selected_project_name, render_view_diffs_and_manage_changes
from project_manager import ProjectManager, PROJECT_LIST_KEY

pm = ProjectManager()

selected_project_name()

# Streamlit page title
st.title("Start Story Object")

story = pm.load_story()
author, author_email = story.author, story.author_email
    
def get_git_author_info():
    """Get the author name and email from the git config."""
    name_command = ["git", "config", "user.name"]
    email_command = ["git", "config", "user.email"]

    name = subprocess.check_output(name_command, universal_newlines=True).strip()
    email = subprocess.check_output(email_command, universal_newlines=True).strip()

    return name, email


# If git is installed and setup and we don't already have an author set on the story, get the author name and email
if not author:
    try:
        author, author_email = get_git_author_info()
    except Exception:
        st.write("Unable to retrieve Git author information. Defaulting to system user.")
        author, author_email = getpass.getuser(), ""


st.markdown("""
## Set the Stage
Let's set the stage for an incredible storytelling adventure!  
Define the root input prompt, which will serve as the creative spark for the entire narrative.  
This prompt is where it all begins—our LLMs will dive into it, weaving an entire world of scenes, characters, and plot twists.
""")


st.markdown("""
### Example Prompts
 > Graphic novel about an astronaut who is the sole survivor of a disastrous Mars expedition.

 > A historical drama novel about a secret guild of architects manipulating iconic buildings to hide a relic.

 > The Office: Anime Version.

 > Vampires and Werewolves unite against a bigger threat as a comic book.

 > Harry Potter, but it's a cooking competition in cartoon form for a kids book.

""")

# Default prompt
default_value = story.prompt or deindent("""
    
""")

# Input for story prompt
STORY_PROMPT = st.text_area(
    "What kind of story do you want to make?",
    value=default_value,
    # height=200
)


st.markdown("### Your Story Prompt")
st.markdown(f"> {STORY_PROMPT.replace('\n', '\n> ')}")

# Input for author name
author = st.text_input("Who are you?", value=author)
author_email = st.text_input("Optional email:", value=author_email)

st.markdown("### Author")
st.markdown(f"> {author} <{author_email}>")


st.markdown(f"As we go, we will story the JSON files and other resources in this directory under git control: `{pm.get_current_project_path()}`")
st.markdown("### Click to Save")

# Button to save story
if st.button("Save Story"):
    # Create Story object
    
    story = story or Story()
    story.prompt = STORY_PROMPT
    story.author = author
    story.author_email = author_email
    
    # Save story as JSON to disk
    story_file = pm.save_story(story)
    
    st.success(f"Story saved to {story_file}!")
    # st.rerun()
    
view_diffs_and_manage_changes()


