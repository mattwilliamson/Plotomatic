import streamlit as st
import json
import os
from pathlib import Path
from models.story import Story
import settings
from plotomatic.utils.story_utils import deindent
import getpass
import subprocess
from plotomatic.utils.streamlit_utils import display_story, display_diff
from components import project_selector, view_diffs_and_manage_changes, selected_project_name, render_view_diffs_and_manage_changes
from project_manager import get_project_manager, PROJECT_LIST_KEY

pm = get_project_manager()

selected_project_name()

# Load story and chat session for current project
story = pm.load_story()

# If there is no story, redirect to the story creation page
if not story:
    st.switch_page("pages/00_Select_Project.py")

# Streamlit page title
st.title("✨ Start Story Object")

story = pm.load_story()
author, author_email = story.author, story.author_email
author_source = pm.get_author_source()  # Get the stored author source
    
def get_git_author_info():
    """Get the author name and email from the git config."""
    name_command = ["git", "config", "user.name"]
    email_command = ["git", "config", "user.email"]

    name = subprocess.check_output(name_command, universal_newlines=True).strip()
    email = subprocess.check_output(email_command, universal_newlines=True).strip()

    return name, email

# Only try to get git info if we haven't already gotten author info from somewhere
if not author and not author_source:
    try:
        author, author_email = get_git_author_info()
        author_source = "Git configuration"
        pm.set_author_source(author_source)
    except Exception:
        st.write("Unable to retrieve Git author information. Defaulting to system user.")
        author, author_email = getpass.getuser(), ""
        author_source = "System username"
        pm.set_author_source(author_source)

st.markdown("""
## 🎭 Set the Stage
Let's set the stage for an incredible storytelling adventure!  
Define the root input prompt, which will serve as the creative spark for the entire narrative.  
This prompt is where it all begins—our LLMs will dive into it, weaving an entire world of scenes, characters, and plot twists.
""")

# Input for author name with info icon if auto-populated
st.subheader("👤 Author")
col1, col2 = st.columns([10, 1])
with col1:
    author = st.text_input("Who are you?", value=author)
with col2:
    if author_source:
        st.write("")  # Add some spacing
        st.write("")  # Add some spacing
        st.info(f"ⓘ Author name was auto-populated from your {author_source}")

author_email = st.text_input("📧 Optional email:", value=author_email)

# st.markdown(f"> {author} <{author_email}>")


st.markdown(f"As we go, we will story the JSON files and other resources in this directory under git control: `{pm.get_current_project_path()}`")

# Button to save story
if st.button("💾 Save Story"):
    # Create Story object
    
    story = story or Story()
    if not author.strip():  # If author is empty or just whitespace
        pm.set_author_source(None)  # Clear the source
    story.author = author
    story.author_email = author_email
    
    # Save story as JSON to disk
    story_file = pm.save_story(story)
    
    st.success(f"Story saved to {story_file}!")
    # st.rerun()
    
    st.markdown("### 📝 Pending Changes")
    st.info("""
        The changes below are **staged** but not yet committed to your story's history. 
        
        Think of this like a draft - you can see what's changed, but these changes aren't permanently saved until you commit them.
        Read more about version control in the section below to understand how git helps track your story's evolution.
    """)
    view_diffs_and_manage_changes()

st.markdown("""
## 📚 Story Management & Version Control
Each story is stored in its own directory under `{settings.STORY_DIR}` and is managed as a separate git repository. 
This means you can:
- Track all changes to your story
- View the complete history of modifications
- Revert to previous versions if needed
- Branch and experiment with different story directions

Git helps you maintain a clear record of how your story evolves. If you're new to git, check out:
- [What is Git?](https://www.perplexity.ai/search/how-would-git-be-useful-to-a-s-wPGh7e8uRuGwDR8SNvEQFw)
""")

