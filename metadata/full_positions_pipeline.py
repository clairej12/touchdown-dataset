import json
import math
import numpy as np
from geopy.distance import geodesic

distance_threshold = 10  # meters

def calculate_bearing(pos1, pos2):
    lat1, lon1 = pos1
    lat2, lon2 = pos2
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    delta_lon = lon2 - lon1
    
    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    initial_bearing = math.atan2(x, y)
    
    return (math.degrees(initial_bearing) + 360) % 360

def densify_path(lat_lng_path, end_heading, distance=distance_threshold):
    dense_path = [lat_lng_path[0]]
    headings = []
    
    for i in range(len(lat_lng_path) - 1):
        start, end = lat_lng_path[i], lat_lng_path[i + 1]
        gap = geodesic(start, end).meters
        bearing = calculate_bearing(start, end)
        headings.append(bearing)
        
        if gap > distance:
            num_points = int(gap // distance)
            latitudes = np.linspace(start[0], end[0], num_points + 1)[1:]
            longitudes = np.linspace(start[1], end[1], num_points + 1)[1:]
            
            for lat, lng in zip(latitudes, longitudes):
                dense_path.append((lat, lng))
                headings.append(bearing)
        
        dense_path.append(end)
    headings.append(end_heading)
    headings = [round(h, 2) for h in headings]
    
    return dense_path, headings

def process_positions(input_file, output_file):
    with open(input_file, 'r') as f:
        positions_data = json.load(f)
    
    for route in positions_data:
        route['lat_lng_path'], route['headings'] = densify_path(route['lat_lng_path'], route['end_heading'])
        del route['route_panoids']
    
    with open(output_file, 'w') as f:
        json.dump(positions_data, f, indent=4)

if __name__ == "__main__":
    input_file = "../data/test_positions_easy.json"
    output_file = "../data/test_positions_easy_processed.json"
    process_positions(input_file, output_file)
