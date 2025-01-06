import json
import numpy as np
from geopy.distance import geodesic
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from graph_loader import GraphLoader  # Replace with the correct module for GraphLoader
import matplotlib.pyplot as plt

# Constants
GRAPH_NODES_FILE = "../graph/nodes.txt"
GRAPH_LINKS_FILE = "../graph/links.txt"

# Function to calculate distances between points
def calculate_distances(panoids, graph):
    distances = []
    for i in range(len(panoids) - 1):
        # Get coordinates for each panoid
        node1 = graph.nodes.get(panoids[i])
        node2 = graph.nodes.get(panoids[i + 1])
        
        if node1 is None or node2 is None:
            print(f"Error: Panoids {panoids[i]} or {panoids[i+1]} not found in graph.")
            continue
        
        coord1 = node1.coordinate
        coord2 = node2.coordinate
        
        # Calculate the geodesic distance
        distance = geodesic(coord1, coord2).meters
        if distance > 100:
            print(f"Warning: Distance between {panoids[i]} and {panoids[i+1]} is unusually large: {distance:.2f} meters.")
        distances.append(distance)
    
    return distances

# Main function
def main(json_file_path):
    # Load the graph
    graph = GraphLoader(GRAPH_NODES_FILE, GRAPH_LINKS_FILE).construct_graph()
    
    all_distances = []  # List to store distances from all routes
    
    # Iterate through routes
    with open(json_file_path, 'r') as f:
        for line in f:
            # Parse each line as a JSON dictionary
            route = json.loads(line.strip())
            
            route_id = route["route_id"]
            panoids = route["route_panoids"]
            
            # Calculate distances
            distances = calculate_distances(panoids, graph)
            if distances:
                all_distances.extend(distances)
            else:
                print(f"No distances computed for route {route_id}.")
    
    if all_distances:
        # Calculate overall statistics
        avg_distance = np.mean(all_distances)
        max_distance = np.max(all_distances)
        min_distance = np.min(all_distances)
        
        # Print overall results
        print(f"Overall Statistics Across All Routes:")
        print(f"Average Distance: {avg_distance:.2f} meters")
        print(f"Max Distance: {max_distance:.2f} meters")
        print(f"Min Distance: {min_distance:.2f} meters")

        plt.hist(all_distances, bins=30, color='blue', alpha=0.7)
        plt.title("Histogram of Distances Between Panoids")
        plt.xlabel("Distance (meters)")
        plt.ylabel("Frequency")
        plt.grid(True)
        plt.savefig("pair_distances_histogram.png")
    else:
        print("No valid distances found across all routes.")

# Run the script
if __name__ == "__main__":
    json_file_path = "../data/test.json"  # Replace with your JSON file path
    main(json_file_path)
