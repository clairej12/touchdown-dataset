import streamlit as st
import pandas as pd
import os
import json

SAMPLE_RANGE = list(range(0, 15))

# Set up paths to images and initialize the annotation DataFrame
image_folder = "./panoids/"
map_folder = "./maps/"

if "test_positions" not in st.session_state:
    with open("test_positions.json", "r") as f:
        print("Loading test positions...")
        test_positions = json.load(f)
    st.session_state.test_positions = test_positions
else:
    test_positions = st.session_state.test_positions

output_file = "annotations.csv"

# Check if an existing annotations file exists
if os.path.exists(output_file):
    annotations_df = pd.read_csv(output_file)
    annotations_df = annotations_df.astype({'Turns': 'str', 'Landmarks': 'str'})
    annotations_df.Turns = annotations_df.Turns.replace('nan', '')
    annotations_df.Landmarks = annotations_df.Landmarks.replace('nan', '')
else:
    # Initialize annotations DataFrame
    annotations_df = pd.DataFrame({
        'sample_idx': SAMPLE_RANGE,
        'route_id': [test_positions[i]['route_id'] for i in SAMPLE_RANGE],
        'Marker': [None] * len(SAMPLE_RANGE),
        'Turns': [''] * len(SAMPLE_RANGE),
        'Landmarks': [''] * len(SAMPLE_RANGE),
    })

# Initialize session state for navigation
if "current_sample_idx" not in st.session_state:
    st.session_state.current_sample_idx = 0

# Helper function to navigate
def navigate_sample(direction, inputs):
    marker, turns, landmarks = inputs
    # Save updates to DataFrame
    annotations_df.loc[st.session_state.current_sample_idx, 'Marker'] = int(marker) if marker else None
    annotations_df.loc[st.session_state.current_sample_idx, 'Turns'] = turns
    annotations_df.loc[st.session_state.current_sample_idx, 'Landmarks'] = landmarks
    save_annotations()

    st.session_state.current_sample_idx += direction
    st.session_state.current_sample_idx = st.session_state.current_sample_idx % len(SAMPLE_RANGE)

def save_annotations():
    annotations_df.to_csv(output_file, index=False)

def save_field(df_field, st_field):
    annotations_df.loc[st.session_state.current_sample_idx, df_field] = st.session_state[st_field]
    save_annotations()

# Get current sample index
sample_idx = SAMPLE_RANGE[st.session_state.current_sample_idx]
sample = test_positions[sample_idx]

# Display current sample information
st.title(f"Sample {st.session_state.current_sample_idx + 1}/{len(SAMPLE_RANGE)}")
st.write(f"Route id: {sample['route_id']}")

# Display all images in the current sample
map_img = os.path.join(map_folder, f'test_route_{sample['route_id']}.png')
ground_truth_position = sample.get("ground_truth_position", {})
path_index = ground_truth_position.get("path_index")
image_paths = []
for i, img in enumerate(sample['route_panoids'][:path_index+1]):
    if i % 5 == 0:
        image_paths.append(map_img)
    image_paths.append(os.path.join(image_folder, img+'.jpg'))
image_paths.append(map_img)
for img_path in image_paths:
    st.image(img_path, use_container_width=True)

# Annotation fields
marker = st.radio(
    "Which marker correctly labels your ending location?",
    [1, 2, 3, 4, 5],
    index=[1, 2, 3, 4, 5].index(annotations_df.loc[st.session_state.current_sample_idx, 'Marker'])
    if pd.notna(annotations_df.loc[st.session_state.current_sample_idx, 'Marker']) else None,
)

turns = st.text_area(
    "Turns (comma separated):",
    value=annotations_df.loc[st.session_state.current_sample_idx, 'Turns'],
    key="turns",
    on_change=save_field,
    args=("Turns","turns"),
)

landmarks = st.text_area(
    "Landmarks (comma separated):",
    value=annotations_df.loc[st.session_state.current_sample_idx, 'Landmarks'],
    key="landmarks",
    on_change=save_field,
    args=("Landmarks","landmarks"),
)

# Navigation buttons
col1, col2, col3 = st.columns([0.2, 0.6, 0.2])
col1.button("Previous", on_click=navigate_sample, args=(-1, (marker, turns, landmarks)))
col3.button("Next", on_click=navigate_sample, args=(1, (marker, turns, landmarks)))

st.write(f"Sample {st.session_state.current_sample_idx + 1}/{len(SAMPLE_RANGE)}")

# Save annotations to CSV
if st.button("Finish Annotations"):
    annotations_df.to_csv(output_file, index=False)
    st.success(f"Annotations saved to {output_file}!")
