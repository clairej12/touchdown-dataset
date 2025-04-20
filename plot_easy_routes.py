import json
from graph_loader import GraphLoader
import gmplot
import random
import geopy.distance
import os
import pdb
import numpy as np
import sys
sys.path.append('./maps/')
from create_html import update_html_markers, CustomGoogleMapPlotter

from pdb import set_trace as dbg

def compute_min_dist(positions):
    min_dist = float('inf')
    for i in range(len(positions)):
        for j in range(i+1, len(positions)):
            dist = geopy.distance.distance((positions[i]["latitude"], positions[i]["longitude"]), 
                                           (positions[j]["latitude"], positions[j]["longitude"])).m
            if dist < min_dist:
                min_dist = dist
    return min_dist

def assert_min_dist(positions, min_dist):
    new_positions = [positions[0]]
    for pos in positions[1:]:
        if all(geopy.distance.distance((pos["latitude"], pos["longitude"]), 
                                       (pt["latitude"], pt["longitude"])).m >= min_dist for pt in new_positions):
            new_positions.append(pos)
    return new_positions

class RouteProcessor:
    def __init__(self, api_key):
        self.api_key = api_key
        self.partition = None
        self.routes = []
        self.turns = {}
    
    def load_routes(self, json_file):
        with open(json_file, 'r') as f:
            self.routes = json.load(f)

        self.partition = "test" if "test" in json_file else "train"            
        
        return self.routes

    def plot_routes(self, routes):
        os.makedirs("/data/claireji/maps/easy_maps/", exist_ok=True)
        for route in routes:
            route_id = route["route_id"]
            # Separate latitudes and longitudes from the lat_lng_path
            latitudes, longitudes = zip(*route["lat_lng_path"])
            
            north_bound = max(latitudes)
            south_bound = min(latitudes)
            east_bound = max(longitudes)
            west_bound = min(longitudes)
            # Initialize the map centered on the route's starting location
            gmap = CustomGoogleMapPlotter(
                sum(latitudes)/len(latitudes), sum(longitudes)/len(longitudes), zoom=20, apikey=api_key, 
                map_type = 'hybrid', bounds = [(south_bound, west_bound), (north_bound, east_bound)]
            )
            
            # Plot the route path with scatter points and a line connecting them
            gmap.scatter(latitudes, longitudes, '#FF0000', size=1, marker=False)
            gmap.plot(latitudes, longitudes, 'white', edge_width=10)
            gmap.marker(latitudes[0], longitudes[0], color='#FFC0CB', label='S')
            gmap.marker(latitudes[-1], longitudes[-1], color='#90EE90', label='G')

            # Plot the selected positions with markers
            for i, position in enumerate(route['multiple_choice_positions']):
                gmap.marker(position['latitude'], position['longitude'], color='cornflowerblue', label=str(i+1))
            
            # Draw the map to an HTML file with a unique name for each route
            map_filename = f"/data/claireji/maps/easy_maps/{self.partition}_easy_route_{route_id}.html"
            gmap.draw(map_filename)
            print(f"Map for route {route_id} saved as {map_filename}")
            update_html_markers(map_filename, map_filename)  

    def select_positions(self, route, num_positions=3, min_distance_m=50):
        """
        Selects an intermediate ground truth position from the route and several other
        random positions, both on and off the route.
        
        Parameters:
        - route: A dictionary containing a 'lat_lng_path' and 'route_panoids' from the loaded routes.
        - num_positions: Total number of positions to return, including the ground truth position.
        
        Returns:
        - A list of dictionaries containing the selected positions with longitude, latitude, and panoid.
        - The ground truth position with its index, panoid, latitude, and longitude.
        """
        num_turns, turns_idx = self.turns[route["route_id"]]
        lat_lng_path = route["lat_lng_path"]
        route_panoids = route["route_panoids"]

        if len(lat_lng_path) <= 4:
            print(f"Route {route['route_id']} has <= 4 coordinates.")
            return None, None, None
        
        if num_turns < 1:
            print(f"Route {route['route_id']} has 0 turns.")
            return None, None, None

        if len(route_panoids) not in turns_idx:
            turns_idx.append(len(route_panoids)-1)
        prev_bound = 1
        on_path_positions = []
        for turn in turns_idx:
            if turn > prev_bound+1:
                pos = random.sample(list(range(prev_bound, turn)), 1)
                prev_bound = turn
                on_path_positions += pos

        positions = [{"panoid": route_panoids[i], 
                      "latitude": lat_lng_path[i][0], 
                      "longitude": lat_lng_path[i][1],
                      "on_path": True,
                      "on_path_positions": i} for i in on_path_positions]
        
        positions = assert_min_dist(positions, min_distance_m)
        if len(positions) < num_positions-1:
            print(f"Route {route['route_id']} has less than {num_positions} candidates.")
            return None, None, None
        on_path_positions = [pos["on_path_positions"] for pos in positions]

        if len(positions) > num_positions:
            pos = np.linspace(0, len(on_path_positions)-1, num_positions, dtype=int)
            on_path_positions = [on_path_positions[i] for i in pos]

        # Select a ground truth position as an intermediate point in the route
        ground_truth_pos = random.randint(0, len(on_path_positions) - 1)
        ground_truth_index = on_path_positions[ground_truth_pos]
        ground_truth_position = {
            "path_index": ground_truth_index,
            "panoid": route_panoids[ground_truth_index],
            "latitude": lat_lng_path[ground_truth_index][0],
            "longitude": lat_lng_path[ground_truth_index][1]
        }

        positions = [{"panoid": route_panoids[i], 
                      "latitude": lat_lng_path[i][0], 
                      "longitude": lat_lng_path[i][1],
                      "on_path": True} for i in on_path_positions]
        
        min_dist = compute_min_dist(positions)
        if min_dist < min_distance_m:
            print(f"Min dist for Route {route['route_id']}: {min_dist}")
            print(f"len(positions): {len(positions)}, on_path_positions: {on_path_positions}")

        # Generate a few off-path random coordinates (for simplicity, within nearby range)
        while len(positions) <= num_positions-1:
            lat_variation = random.choice([random.uniform(0.0003, 0.001), random.uniform(-0.0004, -0.001)])
            lng_variation = random.choice([random.uniform(0.0003, 0.001), random.uniform(-0.0004, -0.001)])
            
            longitude = ground_truth_position["longitude"] + lng_variation
            latitude = ground_truth_position["latitude"] + lat_variation

            if all(geopy.distance.distance((latitude, longitude), (pt["latitude"], pt["longitude"])).m >= min_distance_m for pt in positions):
                positions.append({
                    "panoid": None,
                    "latitude": latitude,
                    "longitude": longitude,
                    "on_path": False
                })
        
        # Combine on-path and off-path positions with the ground truth
        for pos in positions:
            pos["distance_from_correct"] = geopy.distance.distance((pos["latitude"], 
                                                       pos["longitude"]), 
                                                      (ground_truth_position["latitude"], 
                                                       ground_truth_position["longitude"])).m
        idx_shuffle = list(range(len(positions)))
        random.shuffle(idx_shuffle)

        shuffled_positions = []
        gt_idx = 0
        for i, id in enumerate(idx_shuffle):
            shuffled_positions.append(positions[id])
            positions[id]["mc_num"] = i+1
            if positions[id]["panoid"] == ground_truth_position["panoid"]:
                gt_idx = i+1

        ground_truth_position["mc_index"] = gt_idx
        return shuffled_positions, ground_truth_position, min_dist
    
    def save_positions(self, routes, output_file):
        """
        Updates each route with selected positions and ground truth information, 
        then saves the modified routes data to a JSON file.

        Parameters:
        - routes: List of route dictionaries, each containing a 'lat_lng_path' and 'route_panoids'.
        - output_file: Path to the JSON file where the updated routes will be saved.
        """
        updated_routes = []
        min_dists = []

        for i, route in enumerate(routes):
            # Select positions and ground truth for the current route
            positions, ground_truth_position, min_dist = self.select_positions(route)
            if not positions:
                print(f"Route {route['route_id']} has no positions chosen.")
                continue
            # Update the current route with selected positions and ground truth
            route["multiple_choice_positions"] = positions
            route["ground_truth_position"] = ground_truth_position
            
            # Append the updated route to the list
            updated_routes.append(route)
            min_dists.append(min_dist)

        # Save the updated routes to a file
        with open(output_file, 'w') as f:
            json.dump(updated_routes, f, indent=2)

        print(f"Updated routes data saved to {output_file}")
        print(f"Min dist: {min(min_dists)}")
        return updated_routes
    
    def load_positions(self, path):
        self.partition = path.split('.')[0].split('/')[-1].split('_')[0]
        with open(path, 'r') as f:
            self.positions = json.load(f)
        return self.positions
    
    def count_turns(self, route_turns_path):
        with open(route_turns_path, "r") as f:
            route_turns = json.load(f)
        for route in route_turns:
            turns = route["directions"]
            num_turns = 0
            turn_idx = []
            for i, turn in enumerate(turns):
                if turn["direction"] != "Forward":
                    num_turns += 1
                    turn_idx.append(i)
            self.turns[route["route_id"]] = (num_turns, turn_idx)

# Usage
if __name__ == "__main__":
    # Google Maps API key
    split = "test"
    api_key = os.getenv("MAPS_API_KEY")
    if api_key is None:
        raise ValueError("API key not found. Please set the MAPS_API_KEY environment variable.")
    else:
        print("API key loaded successfully.")
    
    # Process routes from JSON file
    route_processor = RouteProcessor(api_key)
    route_processor.count_turns(f"metadata/turns_augmented.json")
    routes = route_processor.load_routes(f'data/{split}_positions_augmented_consolidated.json')
    routes = route_processor.save_positions(routes, f'data/{split}_positions_easy.json')
    print("Produced", len(routes), "routes.")

    routes = route_processor.load_positions(f'data/{split}_positions_easy.json')
    
    plotted_routes = routes
    route_processor.plot_routes(plotted_routes)

    # Print each route's lat/lng path for inspection
    # for route in plotted_routes:
    #     print("Route length:", len(route['route_panoids']))
    #     print("Navigation Text:", route['navigation_text'])
    #     print("Start Heading:", route['start_heading'])
    #     print("End Heading:", route['end_heading'])
    #     print("Lat/Lng Path:", route['lat_lng_path'])
    #     print("==================================")
