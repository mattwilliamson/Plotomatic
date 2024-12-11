import streamlit as st
from plotomatic.components import render_sidebar
from plotomatic.config import load_config

def main():
    st.set_page_config(
        page_title="Plotomatic",
        page_icon="📚",
        layout="wide"
    )
    
    # Load configuration
    config = load_config()
    
    # Render sidebar
    render_sidebar()
    
    # Main content area
    st.title("Plotomatic")
    st.write("Your AI-powered story planning assistant")

if __name__ == "__main__":
    main() 