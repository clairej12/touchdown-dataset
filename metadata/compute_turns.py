import json
import math

# Function to calculate the initial bearing between two points
def calculate_bearing(lat1, lon1, lat2, lon2):
    # Convert degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    delta_lon = lon2 - lon1

    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    initial_bearing = math.atan2(x, y)

    # Convert radians to degrees and normalize
    return (math.degrees(initial_bearing) + 360) % 360

# Function to determine movement direction based on bearings
def get_direction(bearing1, bearing2):
    angle = (bearing2 - bearing1 + 360) % 360
    if angle < 45 or angle > 315:
        return "Forward"
    elif 15 <= angle <= 180:
        return "Right"
    else:
        return "Left"

# Function to process a single dictionary
def process_path(data):
    lat_lng_path = data.get("lat_lng_path", [])
    route_panoids = data.get("image_list", [])
    
    if len(lat_lng_path) < 2 or len(route_panoids) < 2:
        return []

    directions = []
    for i in range(len(lat_lng_path)-1):
        if i > 0:
            lat1, lon1 = lat_lng_path[i-1]
            lat2, lon2 = lat_lng_path[i]
            bearing1 = calculate_bearing(lat1, lon1, lat2, lon2)
            lat3, lon3 = lat_lng_path[i + 1]
            bearing2 = calculate_bearing(lat2, lon2, lat3, lon3)
            direction = get_direction(bearing1, bearing2)            
            panoid_start = route_panoids[i-1]
            panoid_middle = route_panoids[i]
            panoid_end = route_panoids[i+1]

            directions.append({
                "direction": direction,
                "panoid_start": panoid_start,
                "panoid_middle": panoid_middle,
                "panoid_end": panoid_end,
                "bearing_1": bearing1,
                "bearing_2": bearing2
            })

    return directions

# Function to read and process the JSON file
def process_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    results = []
    for entry in data:
        directions = process_path(entry)
        results.append({
            "route_id": entry.get("route_id"),  # Add an identifier if available
            "directions": directions
        })

    return results

# Save results to a new JSON file
def save_results_to_file(results, output_file):
    with open(output_file, 'w') as file:
        json.dump(results, file, indent=4)

# Example usage
input_file = "../data/test_positions_augmented_mapped.json"
output_file = "turns_augmented_mapped.json"

results = process_json_file(input_file)
save_results_to_file(results, output_file)

print("Processing complete. Results saved to", output_file)
