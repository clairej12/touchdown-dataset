import json
import math
import time
import numpy as np
from geopy.distance import geodesic

# --- Configuration Parameters ---
distance_threshold = 5  # Target maximum gap (in meters) between points after interpolation
rdp_epsilon = 0.00005    # Tolerance for RDP simplification (in degrees, adjust as needed)

# --- RDP Implementation ---
def perpendicular_distance(point, line_start, line_end):
    """Compute the perpendicular distance from `point` to the line defined by `line_start` and `line_end`."""
    x0, y0 = point
    x1, y1 = line_start
    x2, y2 = line_end
    # If line_start == line_end, return Euclidean distance.
    if (x1, y1) == (x2, y2):
        return math.hypot(x0 - x1, y0 - y1)
    
    # Compute area of triangle and then the distance:
    area = abs(x1*(y2-y0) + x2*(y0-y1) + x0*(y1-y2))
    base = math.hypot(x2 - x1, y2 - y1)
    return area / base

def rdp(points, epsilon):
    """
    Simplify a list of points using the Ramer-Douglas-Peucker (RDP) algorithm.
    Returns a list of points that approximate the original path.
    """
    if len(points) < 3:
        return points

    start = points[0]
    end = points[-1]
    max_dist = 0
    index = 0
    for i in range(1, len(points)-1):
        d = perpendicular_distance(points[i], start, end)
        if d > max_dist:
            max_dist = d
            index = i

    if max_dist > epsilon:
        # Recursively simplify
        rec_results1 = rdp(points[:index+1], epsilon)
        rec_results2 = rdp(points[index:], epsilon)
        # Avoid duplicate endpoint
        return rec_results1[:-1] + rec_results2
    else:
        return [start, end]

# --- Heading Calculation ---
def calculate_bearing(pos1, pos2):
    """Calculate the bearing (in degrees) between pos1 and pos2."""
    lat1, lon1 = pos1
    lat2, lon2 = pos2
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    delta_lon = lon2 - lon1
    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(delta_lon)
    initial_bearing = math.atan2(x, y)
    return (math.degrees(initial_bearing) + 360) % 360

# --- Densification Function ---
def densify_path(lat_lng_path, end_heading, distance=distance_threshold):
    """
    Interpolate additional points between original points such that the gap is less than `distance` (in meters).
    Also computes a heading for each segment.
    Returns a tuple: (dense_path, headings)
    """
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

# --- Smoothing Headings with a Circular Moving Average ---
def smooth_headings(headings, window_size=5):
    """
    Smooths a list of headings (in degrees) using a circular moving average.
    window_size should be an odd number for a symmetric window.
    Returns a list of smoothed headings.
    """
    n = len(headings)
    smoothed = []
    for i in range(n):
        # Define window limits
        start = max(0, i - window_size // 2)
        end = min(n, i + window_size // 2 + 1)
        window = headings[start:end]
        sin_sum = sum(math.sin(math.radians(h)) for h in window)
        cos_sum = sum(math.cos(math.radians(h)) for h in window)
        avg_heading = math.degrees(math.atan2(sin_sum, cos_sum)) % 360
        smoothed.append(round(avg_heading, 2))
    return smoothed

# --- Process Route ---
def process_route(route):
    """
    Processes a route by:
      1. Simplifying the path with RDP,
      2. Densifying (interpolating) between key points,
      3. Computing and then smoothing the headings.
    Updates the route in-place by replacing 'lat_lng_path' and 'headings' with processed data.
    """
    original_path = route["lat_lng_path"]
    # Step 1: Simplify with RDP to remove small noisy fluctuations.
    simplified_path = rdp(original_path, rdp_epsilon)
    
    # Step 2: Densify the simplified path.
    dense_path, headings = densify_path(simplified_path, route["end_heading"], distance=distance_threshold)
    
    # Optional: Print out the number of points before and after.
    print(f"Original points: {len(original_path)}, simplified: {len(simplified_path)}, densified: {len(dense_path)}")
    
    # Step 3: Smooth the headings with a circular moving average.
    smoothed_headings = smooth_headings(headings, window_size=5)
    
    # Update route: remove original keys and add the new processed path and headings.
    del route['route_panoids']
    del route['multiple_choice_positions']
    del route['ground_truth_position']
    route["lat_lng_path"] = dense_path
    route["headings"] = smoothed_headings

def process_positions(input_file, output_file):
    with open(input_file, 'r') as f:
        positions_data = json.load(f)
    
    for route in positions_data:
        process_route(route)
        
    with open(output_file, 'w') as f:
        json.dump(positions_data, f, indent=4)

if __name__ == "__main__":
    input_file = "../data/test_positions_easy.json"
    output_file = "../data/test_positions_easy_processed.json"
    process_positions(input_file, output_file)

# # Note: to get the turns, run compute_turns.py
# import json
# import math
# import numpy as np
# from geopy.distance import geodesic

# distance_threshold = 10  # meters

# def calculate_bearing(pos1, pos2):
#     lat1, lon1 = pos1
#     lat2, lon2 = pos2
    
#     lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
#     delta_lon = lon2 - lon1
    
#     x = math.sin(delta_lon) * math.cos(lat2)
#     y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
#     initial_bearing = math.atan2(x, y)
    
#     return (math.degrees(initial_bearing) + 360) % 360

# def densify_path(lat_lng_path, end_heading, distance=distance_threshold):
#     dense_path = [lat_lng_path[0]]
#     headings = []
    
#     for i in range(len(lat_lng_path) - 1):
#         start, end = lat_lng_path[i], lat_lng_path[i + 1]
#         gap = geodesic(start, end).meters
#         bearing = calculate_bearing(start, end)
#         headings.append(bearing)
        
#         if gap > distance:
#             num_points = int(gap // distance)
#             latitudes = np.linspace(start[0], end[0], num_points + 1)[1:]
#             longitudes = np.linspace(start[1], end[1], num_points + 1)[1:]
            
#             for lat, lng in zip(latitudes, longitudes):
#                 dense_path.append((lat, lng))
#                 headings.append(bearing)
        
#         dense_path.append(end)
#     headings.append(end_heading)
#     headings = [round(h, 2) for h in headings]
    
#     return dense_path, headings

# def process_positions(input_file, output_file):
#     with open(input_file, 'r') as f:
#         positions_data = json.load(f)
    
#     for route in positions_data:
#         route['lat_lng_path'], route['headings'] = densify_path(route['lat_lng_path'], route['end_heading'])
#         del route['route_panoids']
    
#     with open(output_file, 'w') as f:
#         json.dump(positions_data, f, indent=4)

# if __name__ == "__main__":
#     input_file = "../data/test_positions_easy.json"
#     output_file = "../data/test_positions_easy_processed.json"
#     process_positions(input_file, output_file)
