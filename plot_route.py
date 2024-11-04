import json
from graph_loader import GraphLoader
import gmplot
import random
import geopy.distance
import os

from pdb import set_trace as dbg

class RouteProcessor:
    def __init__(self, graph, api_key):
        self.graph = graph
        self.api_key = api_key
        self.partition = None
        self.routes = []
    
    def load_routes(self, json_file):
        data = []
        with open(json_file, 'r') as f:
            for line in f:
                route_data = json.loads(line)
                data.append(route_data)

        self.partition = json_file.split('.')[0].split('/')[-1]

        for route_data in data:
            navigation_text = route_data['navigation_text']
            route_panoids = route_data['route_panoids']
            start_heading = route_data['start_heading']
            end_heading = route_data['end_heading']
            route_id = route_data["route_id"]
            
            # Build list of (lat, lng) pairs for the route
            lat_lng_path = []
            for panoid in route_panoids:
                if panoid in self.graph.nodes:
                    lat, lng = self.graph.nodes[panoid].coordinate
                    lat_lng_path.append((lat, lng))
                else:
                    print(f"Warning: Panoid {panoid} not found in graph nodes.")

            self.routes.append({
                "route_id": route_id,
                "navigation_text": navigation_text,
                "start_heading": start_heading,
                "end_heading": end_heading,
                "route_panoids": route_panoids,
                "lat_lng_path": lat_lng_path
            })
        
        return self.routes

    def plot_routes(self, routes):
        for route in routes:
            route_id = route["route_id"]
            # Separate latitudes and longitudes from the lat_lng_path
            latitudes, longitudes = zip(*route["lat_lng_path"])
            
            north_bound = max(max(latitudes), max(p['latitude'] for p in route['multiple_choice_positions']))
            south_bound = min(min(latitudes), min(p['latitude'] for p in route['multiple_choice_positions']))
            east_bound = max(max(longitudes), max(p['longitude'] for p in route['multiple_choice_positions']))
            west_bound = min(min(longitudes), min(p['longitude'] for p in route['multiple_choice_positions']))
            # Initialize the map centered on the route's starting location
            gmap = gmplot.GoogleMapPlotter(
                sum(latitudes)/len(latitudes), sum(longitudes)/len(longitudes), 20, apikey=self.api_key, 
                fit_bounds = {'north':north_bound, 'south':south_bound, 'east':east_bound, 'west':west_bound}
            )
            
            # Plot the route path with scatter points and a line connecting them
            gmap.scatter(latitudes, longitudes, '#FF0000', size=1, marker=False)
            gmap.plot(latitudes, longitudes, 'cornflowerblue', edge_width=5)
            gmap.marker(latitudes[0], longitudes[0], color='#FFC0CB', label='S')
            gmap.marker(latitudes[-1], longitudes[-1], color='#90EE90', label='G')

            # Plot the selected positions with markers
            for i, position in enumerate(route['multiple_choice_positions']):
                gmap.marker(position['latitude'], position['longitude'], color='cornflowerblue', label=str(i+1))
            
            # Draw the map to an HTML file with a unique name for each route
            map_filename = f"maps/{self.partition}_route_{route_id}.html"
            gmap.draw(map_filename)
            print(f"Map for route {route_id} saved as {map_filename}")

    def select_positions(self, route, num_positions=5, min_distance_m=50):
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
        lat_lng_path = route["lat_lng_path"]
        route_panoids = route["route_panoids"]

        # Select a ground truth position as an intermediate point in the route
        ground_truth_index = random.randint(1, len(lat_lng_path) - 2)
        ground_truth_position = {
            "path_index": ground_truth_index,
            "panoid": route_panoids[ground_truth_index],
            "latitude": lat_lng_path[ground_truth_index][0],
            "longitude": lat_lng_path[ground_truth_index][1]
        }
        
        # Collect random positions on the route (excluding the ground truth position)
        on_path_positions = random.sample(
            [i for i in range(1,len(lat_lng_path)-1) if abs(i-ground_truth_index) > 1], 
            min(num_positions // 2, max(len(lat_lng_path) - 5, 0))
        ) if len(lat_lng_path) > 4 else []

        positions = [{"panoid": route_panoids[i], "latitude": lat_lng_path[i][0], "longitude": lat_lng_path[i][1]} for i in on_path_positions]

        # Generate a few off-path random coordinates (for simplicity, within nearby range)
        while len(positions)+1 <= num_positions-1:
            lat_variation = random.choice([random.uniform(0.0002, 0.001), random.uniform(-0.0007, -0.001)])
            lng_variation = random.choice([random.uniform(0.0002, 0.001), random.uniform(-0.0007, -0.001)])
            
            longitude = ground_truth_position["longitude"] + lng_variation
            latitude = ground_truth_position["latitude"] + lat_variation

            if all(geopy.distance.distance((latitude, longitude), (pt["latitude"], pt["longitude"])).m >= min_distance_m for pt in positions):
                positions.append({
                    "panoid": None,
                    "latitude": latitude,
                    "longitude": longitude
                })
        
        # Combine on-path and off-path positions with the ground truth
        random.shuffle(positions)
        for pos in positions:
            pos["distance_from_correct"] = geopy.distance.distance((pos["latitude"], 
                                                       pos["longitude"]), 
                                                      (ground_truth_position["latitude"], 
                                                       ground_truth_position["longitude"])).m
        i = random.randint(0, len(positions))
        positions.insert(i, ground_truth_position)  # Insert ground truth
        ground_truth_position["mc_index"] = i

        return positions, ground_truth_position
    
    def save_positions(self, routes, output_file):
        """
        Updates each route with selected positions and ground truth information, 
        then saves the modified routes data to a JSON file.

        Parameters:
        - routes: List of route dictionaries, each containing a 'lat_lng_path' and 'route_panoids'.
        - output_file: Path to the JSON file where the updated routes will be saved.
        """
        updated_routes = []

        for i, route in enumerate(routes):
            # Select positions and ground truth for the current route
            positions, ground_truth_position = self.select_positions(route)
            
            # Update the current route with selected positions and ground truth
            route["multiple_choice_positions"] = positions
            route["ground_truth_position"] = ground_truth_position
            
            # Append the updated route to the list
            updated_routes.append(route)

        # Save the updated routes to a file
        with open(output_file, 'w') as f:
            json.dump(updated_routes, f, indent=2)

        print(f"Updated routes data saved to {output_file}")
        return updated_routes
    
    def load_positions(self, path):
        self.partition = path.split('.')[0].split('/')[-1].split('_')[0]
        with open(path, 'r') as f:
            self.positions = json.load(f)
        return self.positions

# Usage
if __name__ == "__main__":
    # Google Maps API key
    
    api_key = os.getenv("MAPS_API_KEY")
    if api_key is None:
        raise ValueError("API key not found. Please set the MY_API_KEY environment variable.")
    else:
        print("API key loaded successfully.")

    # Initialize graph loader and construct the graph
    graph_loader = GraphLoader()
    graph = graph_loader.construct_graph()
    
    # Process routes from JSON file
    route_processor = RouteProcessor(graph, api_key)
    # routes = route_processor.load_routes('data/test.json')
    # routes = route_processor.save_positions(routes, 'data/test_positions.json')

    routes = route_processor.load_positions('data/test_positions.json')
    
    plotted_routes = routes[:]
    route_processor.plot_routes(plotted_routes)

    # Print each route's lat/lng path for inspection
    # for route in plotted_routes:
    #     print("Route length:", len(route['route_panoids']))
    #     print("Navigation Text:", route['navigation_text'])
    #     print("Start Heading:", route['start_heading'])
    #     print("End Heading:", route['end_heading'])
    #     print("Lat/Lng Path:", route['lat_lng_path'])
    #     print("==================================")
