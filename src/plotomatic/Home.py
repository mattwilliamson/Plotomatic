"""Home page for the Plotomatic application."""
import streamlit as st
import emoji
from pathlib import Path
from plotomatic.components import render_sidebar
from plotomatic.config import load_config

# Set page config
st.set_page_config(
    page_title="Plotomatic",
    page_icon="📚",
    layout="wide"
)

# Load configuration
config = load_config()

# Render sidebar
render_sidebar()

st.title("Plotomatic")

# Load Markdown file from project root
root_dir = Path(__file__).parent.parent.parent
readme_path = root_dir / "README.md"

try:
    with open(readme_path, "r") as file:
        markdown_content = file.read()

    # Update static file paths to point to the new location
    markdown_content = markdown_content.replace(
        "./app/static/", 
        "./src/plotomatic/static/"
    )

    # Emojis
    markdown_content = emoji.emojize(markdown_content)

    # Display Markdown content
    st.markdown(markdown_content, unsafe_allow_html=True)
except FileNotFoundError:
    st.write("Welcome to Plotomatic! README.md not found.")