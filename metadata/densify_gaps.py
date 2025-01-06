import json
import requests
import os
import numpy as np
from geopy.distance import geodesic
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from graph_loader import GraphLoader, GraphWriter
import pdb

# Configuration
# API_KEY = os.getenv("MAPS_API_KEY")
# OUTPUT_DIR = "/data/claireji/panoids/"
OUTPUT_JSON = "dense_turns.json"
DISTANCE = 10
DATA_FILE = "../data/test_positions.json"
NEW_DATA_FILE = "../data/test_positions_augmented.json"

# Ensure output directory exists
# os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_lat_long(graph, panoid):
    """Retrieve latitude and longitude for a given panoid using a graph."""
    node = graph.nodes.get(panoid)
    if node:
        return node.coordinate
    else:
        raise ValueError(f"Panoid {panoid} not found in the graph.")

def get_sampled_points(start, end, bearing_1, bearing_2, distance):
    gap = geodesic(start, end).meters
    if gap >= 15:
        num_points = int(np.ceil(gap / distance))
        
        """Generate interpolated points between start and end coordinates."""
        latitudes = np.linspace(start[0], end[0], num_points)
        longitudes = np.linspace(start[1], end[1], num_points)
        if bearing_2 < bearing_1:
            bearing_2 += 360
        bearings = np.linspace(bearing_1, bearing_2, num_points)
        bearings = bearings % 360
        # print(f"Distance between {start} and {end}: {gap:.2f} meters, sampling {num_points} points.")
        return list(zip(latitudes, longitudes, bearings))
    return None

def add_to_graph(graph, sampled_points, start_end):
    start_panoid, end_panoid, current_heading = start_end
    current_panoid = start_panoid
    for lat, lng, heading in sampled_points:
        panoid = "panoid_" + f"{lat}_{lng}"
        if panoid not in graph.nodes:
            graph.add_node(panoid, heading, lat, lng)
        while int(current_heading) in graph.nodes[current_panoid].neighbors:
            current_heading += 1
        graph.add_edge(current_panoid, panoid, current_heading)
        current_panoid = panoid
        current_heading = heading
    while int(current_heading) in graph.nodes[current_panoid].neighbors:
        current_heading += 1
    graph.add_edge(current_panoid, end_panoid, current_heading)
    return graph
        
def process_directions(input_file, graph_loader, graph_writer):
    """Main processing function."""
    # Load the input JSON
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    with open(DATA_FILE, 'r') as f:
        positions_data = json.load(f)

    # Load the graph
    graph = graph_loader.construct_graph()

    # Initialize image mapping dictionary
    image_mapping = []
    samples = {}

    for i, route in enumerate(data[:]):
        route_id = route["route_id"]
        dense_turns = []
        new_route_panoids = []
        new_lat_lng_path = []
        for index, direction in enumerate(route["directions"]):
            new_route_panoids.append(direction["panoid_start"])
            new_lat_lng_path.append(fetch_lat_long(graph, direction["panoid_start"]))
            try:
                # Get start and end coordinates
                start_coords = fetch_lat_long(graph, direction["panoid_start"])
                end_coords = fetch_lat_long(graph, direction["panoid_end"])
                bearing_1 = direction["bearing_1"]
                bearing_2 = direction["bearing_2"]

                if samples.get((direction["panoid_start"], direction["panoid_end"])):
                    sampled_points = samples[(direction["panoid_start"], direction["panoid_end"])]
                else:
                    # Get interpolated points
                    sampled_points = get_sampled_points(start_coords, end_coords, bearing_1, bearing_2, DISTANCE)
                    if sampled_points:
                        samples[(direction["panoid_start"], direction["panoid_end"])] = sampled_points
                        graph = add_to_graph(graph, sampled_points, (direction["panoid_start"], direction["panoid_end"], direction["bearing_1"]))

                if not sampled_points:
                    continue
                
                # Fetch and save images
                turn_images = []
                for idx, (lat, lng, heading) in enumerate(sampled_points):
                    file_name = "panoid_" + f"{lat}_{lng}"
                    turn_images.append({'lat': lat, 'lng': lng, 'heading': heading, 'panoid': file_name, 'index': idx})
                    new_route_panoids.append(file_name)
                    new_lat_lng_path.append((lat, lng))

                # Add to dense turns
                dense_turns.append({
                    "step": index,
                    "direction": direction["direction"],
                    "start_panoid": direction["panoid_start"],
                    "end_panoid": direction["panoid_end"],
                    "images": turn_images
                })

            except Exception as e:
                print(f"Error processing route {route_id}, direction {direction}: {e}")
                continue
            
        # Add to image mapping
        image_mapping.append({
            "route_id": route_id,
            "directions": dense_turns
        })

        new_route_panoids.append(direction["panoid_end"])
        new_lat_lng_path.append(fetch_lat_long(graph, direction["panoid_end"]))

        # Update route with new panoids
        positions_data[i]["route_panoids"] = new_route_panoids
        positions_data[i]["lat_lng_path"] = new_lat_lng_path

    graph_writer.write_graph(graph)

    # Save the image mapping to a JSON file
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(image_mapping, f, indent=4)

    with open(NEW_DATA_FILE, 'w') as f:
        json.dump(positions_data, f, indent=4)

if __name__ == "__main__":
    input_file = "turns.json"  # Replace with your actual file path
    graph_loader = GraphLoader("../graph/nodes.txt", "../graph/links.txt")  # Replace with your actual file paths
    graph_writer = GraphWriter("../graph/aug_nodes.txt", "../graph/aug_links.txt")  
    process_directions(input_file, graph_loader, graph_writer)
