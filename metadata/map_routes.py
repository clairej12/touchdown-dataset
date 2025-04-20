import json, math
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from graph_loader import GraphLoader
from graph_loader import GraphWriter
from graph_loader import Graph, Node
import pdb

graph = GraphLoader("../graph/aug_nodes.txt", "../graph/aug_links.txt").construct_graph()

file_path = '../data/test_positions_easy.json'  
with open(file_path, 'r') as file:
    positions = json.load(file)

file_path = '../metadata/test_easy_panoid_mapping.json'  
with open(file_path, 'r') as file:
    panoid_mapping = json.load(file)

def remove_consecutive_repeats(panoids, lat_lng):
    idx_mapping = {0 : 0} # old list index to new list index
    idx = 0
    if not panoids:
        return panoids  # Handle empty list case
    panoid_result = [panoids[0]]  # Start with the first element
    lat_lng_result = [lat_lng[0]]
    for i,item in enumerate(panoids[1:]):
        if item != panoid_result[-1]:  # Add only if different from the last added item
            panoid_result.append(item)
            lat_lng_result.append(lat_lng[i+1])
            idx += 1
        idx_mapping[i+1] = idx
    return panoid_result, lat_lng_result, idx_mapping

# Function to calculate the initial bearing between two points
def calculate_bearing(pos1, pos2):
    lat1, lon1 = pos1
    lat2, lon2 = pos2
    # Convert degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    delta_lon = lon2 - lon1

    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    initial_bearing = math.atan2(x, y)

    # Convert radians to degrees and normalize
    return (math.degrees(initial_bearing) + 360) % 360

def consolidate_nodes(graph, panoid_mapping, test_positions):
    new_graph = Graph()
    new_positions = []
    # Step 1: Reverse mapping from panoid to node names
    panoid_to_nodes = {}
    for node_name, panoid in panoid_mapping.items():
        panoid_to_nodes.setdefault(panoid, []).append(node_name)

    for route in test_positions[:60]:
        new_route = [panoid_mapping[node] for node in route['route_panoids']]

        new_route, new_lat_lng, idx_mapping = remove_consecutive_repeats(new_route, route['lat_lng_path'])

        for option in route["multiple_choice_positions"]:
            option["panoid"] = panoid_mapping[option["panoid"]] if option["panoid"] else None
            if "path_index" in option:
                option["path_index"] = idx_mapping[option["path_index"]]
        route["ground_truth_position"]["panoid"] = panoid_mapping[route["ground_truth_position"]["panoid"]]
        route["ground_truth_position"]["path_index"] = idx_mapping[route["ground_truth_position"]["path_index"]]

        heading_route = []
        for i, panoid in enumerate(new_route):
            current_coord = new_lat_lng[i]
            if panoid not in new_graph.nodes:
                old_panoid = panoid_to_nodes[panoid][0]
                main_node = graph.nodes[old_panoid]
                new_node = Node(panoid, main_node.pano_yaw_angle, current_coord[0], current_coord[1])
                new_graph.nodes[panoid] = new_node
            next_coord = new_lat_lng[i+1] if i < len(new_route) - 1 else None
            if next_coord:
                heading = int(calculate_bearing(current_coord, next_coord))
                if heading in new_graph.nodes[panoid].neighbors:
                    print(f"Duplicate heading {heading} in node {panoid}")
                new_graph.nodes[panoid].neighbors[heading] = new_route[i+1]
            else:
                heading = calculate_bearing(new_lat_lng[i-1], current_coord)
            panoid_name = f"{panoid}_{heading}"
            heading_route.append(panoid_name)
        route['route_panoids'] = new_route
        route['lat_lng_path'] = new_lat_lng
        route['image_list'] = heading_route
        new_positions.append(route)

    for node in new_graph.nodes.values():
        new_neighbors = {}
        for heading, neighbor in node.neighbors.items():
            new_neighbors[heading] = new_graph.nodes[neighbor]
        node.neighbors = new_neighbors

    return new_graph, new_positions

new_graph, new_positions = consolidate_nodes(graph, panoid_mapping, positions)

out_file_path = '../data/test_positions_easy_mapped.json'
with open(out_file_path, 'w') as file:
    json.dump(new_positions, file, indent=2)

graph_writer = GraphWriter(node_file='../graph/easy_nodes_mapped.txt', edge_file='../graph/easy_links_mapped.txt')
graph_writer.write_graph(new_graph)