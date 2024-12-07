# Notes

can't select different project and update chat. it updates both. need to update all the project manager stuff to use session variables so it updates properly.
the creative llm doesn't have context and needs to be made generic

start with a create project
use git to update story - need some functions to commit and list commits and show diffs
use pydantic model to allow editing directly

Use stqdm (https://github.com/Wirg/stqdm) for progress bars

for every single operation:
    - load a story object
    - select model
    - select context size
    - select response size
    - show progress
    - rander a prompt template
    - call ollama with stream=True
    - stream output (render as json if it is json)
    - parse output if json
    - merge into story or overwrite single property
    - show diff
    - save or discard

for every batch operation:    
    - load a story object
    - input a prompt template
    - select model
    - select context size
    - select response size
    - show overall progress bar
    - loop over all characters/acts/chapters/scenes:
    - show progress
    - rander a prompt template
    - call ollama with stream=True
    - stream output (render as json if it is json)
    - parse output if json
    - merge into story or overwrite single property
    - show diff
    - save or discard

progress bars:
    - time elapsed
    - time remaining
    - how many done / total
    - percent

character list page
To show character relationships: https://github.com/rajagurunath/streamlit-react-flow or https://github.com/snehankekre/streamlit-d3graph

chapter browser - https://github.com/Schluca/streamlit_tree_select

To edit rich text: https://github.com/okld/streamlit-quill or https://github.com/marcusschiesser/streamlit-monaco

x no good I think maybe view story object directly with https://github.com/jrieke/streamlit-inspector

pdf viewer: https://github.com/lfoppiano/streamlit-pdf-viewer

timeline: https://github.com/innerdoc/streamlit-timeline or https://github.com/giswqs/streamlit-timeline

progress bar: https://github.com/Wirg/stqdm or https://github.com/TangleSpace/hydralit_components (has navbar too)

another page to chat with an LLM using ollama and streamlit-chat or https://github.com/AI-Yash/st-chat (959) to update the story or https://github.com/undo76/st-chat-message which has markdown support
https://github.com/het-25/st-multimodal-chatinput or https://github.com/osala-eng/st-chat-plus

wordcloud: https://github.com/drogbadvc/st-wordcloud

file browser: https://github.com/hoggatt/st-file-browser

table: https://github.com/victorC97/streamlit_freegrid


cover photo gallery: https://github.com/jrieke/streamlit-image-select or https://github.com/TakedaKatsuji/Streamlit-ImageViewer https://github.com/yevgnen/streamlit-gallery

search box: https://github.com/m-wrzr/streamlit-searchbox

https://github.com/leonfresh/streamlit-disqus

data labeling: https://github.com/deneland/streamlit-labelstudio?tab=readme-ov-file

add grammar to reviewer and require rewrite if there is a violation

ollama json mode with pydantic objects

docker
docker compose
streamlit config
use git to commit each step instead of storing in different directories
user overrides: any fields that will be overritten for all steps
unit tests

how to show progress bars in streamlit?

common methods to execute llm, watch progress, show diff

update model so each dialog will automatically assign to each other on load for easy reference

starting prompt can be a picture!

support different mediums better

use FluxImg2ImgPipeline to enhance the stiched-together images before animating
from diffusers import FluxImg2ImgPipeline

be able to convert between media, like book to video game

chaos monkey to add plot twists

mad libs to make story have a better seed like (pick 6 nouns) and use them in the prompt

todo: make sure there are only characters that are real in scenes and make sure all get included

Test image to image to transplant characters into scenes
Test image to video
Extract props etc

can use image to image to change poses probably using the reference image as a baseline

Image Reviewer
Make sure face is visible and clear

Make sure scene is coherent

Scene builder - add sub images and then do image to image to clean it up, e.g. lighting/shadows etc?
flux rails or whatever it's called


https://github.com/krish-adi/barfi for workflow editing

https://github.com/JohnSnowLabs/nlu for nlu/nlp processing. might be good to identify any people/places things in story

allow transcription over webrtc

something with spacy for nlu word associations or something?


maybe use word annotation with https://github.com/tvst/st-annotated-text?tab=readme-ov-file to highlight characters or something