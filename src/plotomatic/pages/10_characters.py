import streamlit as st
from streamlit_react_flow import react_flow
from project_manager import get_project_manager
from model import CharacterRelationship
import networkx as nx

st.set_page_config(page_title="Character Graph", page_icon="📖", layout="wide")

# Initialize ProjectManager and load the story
pm = get_project_manager()
story = pm.load_story()

# Extract characters and relationships
characters = story.characters

# Build a graph using NetworkX for layout calculation
graph = nx.DiGraph()

# Add nodes
for char in characters:
    graph.add_node(
        char.nickname,
        label=f"{char.name}",
        role=char.role,
        description=char.description,
        personality=char.personality,
        physical_appearance=char.physical_appearance
    )

# Deduplicate edges
unique_edges = set()  # To store (source, target) pairs

for char in characters:
    for rel in char.relationships:
        edge = (char.nickname, rel.character_nickname)
        if edge not in unique_edges:
            unique_edges.add(edge)
            graph.add_edge(char.nickname, rel.character_nickname, label=rel.relationship_type)

# Calculate node degree (connections)
degrees = dict(graph.degree())
max_degree = max(degrees.values()) if degrees else 1

# Use NetworkX's spring layout
positions = nx.spring_layout(graph, scale=1000, center=(0, 0))  # Center nodes for better visualization

# Add a state to track the selected node
if "selected_node_id" not in st.session_state:
    st.session_state.selected_node_id = None

# Convert positions and degrees to React Flow format
elements = []
for node, pos in positions.items():
    font_size = 8 + (degrees[node] / max_degree) * 20  # Scale font size between 8 and 28
    elements.append({
        "id": node,
        "data": {
            "label": graph.nodes[node]["label"],
            "role": graph.nodes[node]["role"],
            "description": graph.nodes[node]["description"],
            "personality": graph.nodes[node]["personality"],
            "physical_appearance": graph.nodes[node]["physical_appearance"]
        },
        "type": "default",
        "position": {"x": pos[0], "y": pos[1]},
        "style": {
            "background": "#add8e6",
            "padding": 10,
            "textAlign": "center",
            "fontSize": f"{font_size}px",  # Adjust font size dynamically
        },
    })

# Add edges
for edge in graph.edges(data=True):
    elements.append({
        "id": f"{edge[0]}-{edge[1]}",
        "source": edge[0],
        "target": edge[1],
        "animated": True,
        "label": edge[2].get("label", ""),  # Optional: show relationship type
    })

# Define graph styles
flow_styles = {"height": "700px", "width": "100%"}

# Render the React Flow graph
clicked_element = react_flow("character_graph", elements=elements, flow_styles=flow_styles)

# Handle node selection
if clicked_element and clicked_element["id"] in graph.nodes:
    st.session_state.selected_node_id = clicked_element["id"]

# Display node details when clicked
if st.session_state.selected_node_id:
    selected_node = graph.nodes[st.session_state.selected_node_id]
    st.markdown(f"### Character Details: {selected_node['label']}")
    st.write(f"**Role:** {selected_node['role']}")
    st.write(f"**Description:** {selected_node['description']}")
    st.write(f"**Personality:** {selected_node['personality']}")
    st.write(f"**Physical Appearance:** {selected_node['physical_appearance']}")
