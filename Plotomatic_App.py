import streamlit as st
import emoji

st.title("Plotomatic Streamlit App")

# Load Markdown file
markdown_file = "README.md"
with open(markdown_file, "r") as file:
    markdown_content = file.read()

# Static files
markdown_content = markdown_content.replace("./static/", "./app/static/")

# Emojis
markdown_content = emoji.emojize(markdown_content)



# Display Markdown content in Streamlit
st.markdown(markdown_content, unsafe_allow_html=True)