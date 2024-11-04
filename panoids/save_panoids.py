import json
import requests
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from graph_loader import GraphLoader
# from streetview import get_panorama_async
# import asyncio

api_key = "AIzaSyAAmbphdlZi8ygelmXSRWO_jt3Dvcgsis8"

def download_street_view_images(graph, route, image_folder):
        """
        Downloads Google Street View images from the start of the route up to the ground truth index.

        Parameters:
        - route: A dictionary containing 'lat_lng_path' and 'route_panoids'.
        - ground_truth_index: The index in the route's panoid list that serves as the ground truth point.
        """
        # Iterate through each node up to the ground truth index
        ground_truth_index = route['ground_truth_position']['path_index']
        for i, panoid in enumerate(route['route_panoids'][:ground_truth_index + 1]):
            image_path = os.path.join(image_folder, f"{panoid}.jpg")
            if os.path.exists(image_path):
                continue

            node = graph.nodes.get(panoid)

            if not node:
                print(f"Node with panoid {panoid} not found in graph.")
                continue

            # Construct the Google Street View API URL
            url = (
                f"https://maps.googleapis.com/maps/api/streetview?"
                f"size=800x600&location={node.coordinate[0]},{node.coordinate[1]}"
                f"&heading={node.pano_yaw_angle}&key={api_key}&fov=120"
            )

            # Request the image from Google Street View API
            response = requests.get(url, stream=True)
            
            # Check if the request was successful
            if response.status_code == 200:
                with open(image_path, 'wb') as f:
                    for chunk in response:
                        f.write(chunk)
                print(f"Saved image for panoid {panoid} at {image_path}")
            else:
                print(f"Failed to retrieve image for panoid {panoid} with status code {response.status_code}")

# async def download_street_view_pano(graph, route, image_folder):
#         """
#         Downloads Google Street View images from the start of the route up to the ground truth index.

#         Parameters:
#         - route: A dictionary containing 'lat_lng_path' and 'route_panoids'.
#         - ground_truth_index: The index in the route's panoid list that serves as the ground truth point.
#         """
#         # Iterate through each node up to the ground truth index
#         ground_truth_index = route['ground_truth_position']['path_index']
#         for i, panoid in enumerate(route['route_panoids'][:ground_truth_index + 1]):
#             node = graph.nodes.get(panoid)

#             if not node:
#                 print(f"Node with panoid {panoid} not found in graph.")
#                 continue

#             image = await get_panorama_async(
#                 pano_id=panoid,
#                 zoom=3,
#                 # api_key=api_key,
#             )
#             image_path = os.path.join(image_folder, f"{panoid}.jpg")
#             image.save(image_path, 'jpeg')
#             print(f"Saved image for panoid {panoid} at {image_path}")

if __name__ == "__main__":
    # Load the graph and routes from JSON files
    graph = GraphLoader("../graph/nodes.txt", "../graph/links.txt").construct_graph()
    with open("../data/test_positions.json", 'r') as f:
        routes = json.load(f)
    
    # Create a folder to store the downloaded images
    image_folder = 'test_images'
    os.makedirs(image_folder, exist_ok=True)
    
    # Download images for each route
    for idx, route in enumerate(routes[5:]):
        download_street_view_images(graph, route, image_folder)
        # asyncio.run(download_street_view_pano(graph, route, image_folder))
