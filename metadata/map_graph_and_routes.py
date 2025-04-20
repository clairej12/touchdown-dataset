import json
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from graph_loader import GraphLoader
from graph_loader import GraphWriter
from graph_loader import Graph, Node
import pdb

file_path = '../data/test_positions_easy.json'  
with open(file_path, 'r') as file:
    positions = json.load(file)

file_path = '../metadata/test_easy_panoid_mapping.json'  
with open(file_path, 'r') as file:
    panoid_mapping = json.load(file)

graph = GraphLoader("../graph/aug_nodes.txt", "../graph/aug_links.txt").construct_graph()

def remove_consecutive_repeats(lst):
    idx_mapping = {0 : 0} # old list index to new list index
    idx = 0
    if not lst:
        return lst  # Handle empty list case
    result = [lst[0]]  # Start with the first element
    for i,item in enumerate(lst[1:]):
        if item != result[-1]:  # Add only if different from the last added item
            result.append(item)
            idx += 1
        idx_mapping[i+1] = idx
    return result, idx_mapping

def consolidate_nodes(graph, panoid_mapping, test_positions):
    new_graph = Graph()
    # Step 1: Reverse mapping from panoid to node names
    panoid_to_nodes = {}
    for node_name, panoid in panoid_mapping.items():
        panoid_to_nodes.setdefault(panoid, []).append(node_name)
    
    # Step 2: Consolidate nodes in the graph
    for panoid, node_list in panoid_to_nodes.items():
        main_node_name = node_list[0]
        main_node = graph.nodes[main_node_name]
        new_node = Node(panoid, main_node.pano_yaw_angle, main_node.coordinate[0], main_node.coordinate[1])

        # Merge neighbors from all nodes that map to this panoid
        new_neighbors = {}
        for node_name in node_list:
            if node_name in graph.nodes:
                node_neighbors = graph.nodes[node_name].neighbors
                for h, n in node_neighbors.items():
                    if n.panoid in panoid_mapping:
                        n_name = panoid_mapping[n.panoid]
                        if n_name not in new_neighbors and n_name != panoid:
                            new_neighbors[n_name] = set([h])
                        elif n_name != panoid:
                            new_neighbors[n_name].add(h)

        new_node.neighbors = new_neighbors
        new_graph.nodes[panoid] = new_node

    for node_name in new_graph.nodes:
        node = new_graph.nodes[node_name]
        new_neighbors = {}
        for neighbor, heading_set in node.neighbors.items():
            for heading in heading_set:
                if heading in new_neighbors: 
                    print(f"Duplicate heading {heading} in node {node_name}")
                new_neighbors[heading] = new_graph.nodes[neighbor]
        node.neighbors = new_neighbors
    
    # Step 3: Update test_positions route
    new_positions = []
    for route in test_positions[:60]:
        new_route = [panoid_mapping[node] for node in route['route_panoids']]

        new_route, idx_mapping = remove_consecutive_repeats(new_route)
        new_lat_lng = [new_graph.nodes[panoid].coordinate for panoid in new_route]

        for option in route["multiple_choice_positions"]:
            option["panoid"] = panoid_mapping[option["panoid"]] if option["panoid"] else None
            if "path_index" in option:
                option["path_index"] = idx_mapping[option["path_index"]]
        route["ground_truth_position"]["panoid"] = panoid_mapping[route["ground_truth_position"]["panoid"]]
        route["ground_truth_position"]["path_index"] = idx_mapping[route["ground_truth_position"]["path_index"]]

        heading_route = []
        for i, panoid in enumerate(new_route):
            neighbors = new_graph.nodes[panoid].neighbors
            if i < len(new_route) - 1:
                try:
                    heading = [h for h, n in neighbors.items() if n.panoid == new_route[i+1]][0]
                except:
                    pdb.set_trace()
                    print(f"Route {route['route_id']} missing link between {panoid} and {new_route[i+1]}")
                    print(f"Neighbors: {[(h, n.panoid)for h, n in neighbors.items()]}")
                    print(f"Original graph: {[[(p, h, panoid_mapping[n.panoid])for h,n in graph.nodes[p].neighbors.items()] for p in panoid_to_nodes[panoid]]}")
            else:
                heading = min(neighbors.keys(), key=lambda k: min(abs(k - heading), 360 - abs(k - heading)))
            panoid_name = f"{panoid}_{heading}"
            heading_route.append(panoid_name)
        route['route_panoids'] = new_route
        route['lat_lng_path'] = new_lat_lng
        route['image_list'] = heading_route
        new_positions.append(route)

    return new_graph, new_positions

new_graph, new_positions = consolidate_nodes(graph, panoid_mapping, positions)

out_file_path = '../data/test_positions_easy_mapped.json'
with open(file_path, 'w') as file:
    json.dump(new_positions, file, indent=2)

graph_writer = GraphWriter(node_file='../graph/easy_nodes_mapped.txt', edge_file='../graph/easy_links_mapped.txt')
graph_writer.write_graph(new_graph)