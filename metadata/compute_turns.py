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
    if angle < 80 or angle > 280:
        return "Forward", angle
    elif 80 <= angle <= 180:
        return "Right", angle
    else:
        return "Left", angle

# Function to process a single dictionary
def process_path(data):
    path = data.get("path", [])
    
    if len(path) < 2:
        return []

    for i, entry in enumerate(path):
        entry["idx"] = i

    directions = []
    turn_list = []
    for i in range(len(path)-1):
        if i > 0:
            lat1, lon1 = path[i-1]["lat"], path[i-1]["lng"]
            lat2, lon2 = path[i]["lat"], path[i]["lng"]
            lat3, lon3 = path[i + 1]["lat"], path[i + 1]["lng"]

            bearing1 = calculate_bearing(lat1, lon1, lat2, lon2)
            bearing2 = calculate_bearing(lat2, lon2, lat3, lon3)

            turn, angle = get_direction(bearing1, bearing2) 

            if turn != "Forward":
                turn_list.append((i, turn))

            panoid_start = path[i-1]
            panoid_middle = path[i]
            panoid_end = path[i+1]

            directions.append({
                "turn": turn,
                "panoid_start": panoid_start,
                "panoid_middle": panoid_middle,
                "panoid_end": panoid_end,
                "bearing_1": bearing1,
                "bearing_2": bearing2,
                "angle": angle
            })

    return directions, turn_list

# Function to read and process the JSON file
def process_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    results = []
    for entry in data:
        directions, turns = process_path(entry)
        results.append({
            "route_id": entry.get("route_id"),  # Add an identifier if available
            "turns": turns,
            "directions": directions,
        })

    return results

# Save results to a new JSON file
def save_results_to_file(results, output_file):
    with open(output_file, 'w') as file:
        json.dump(results, file, indent=4)

# Example usage
input_file = "../data/test_positions_easy_processed_mapped.json"
output_file = "test_positions_easy_processed_turns.json"

results = process_json_file(input_file)
save_results_to_file(results, output_file)

print("Processing complete. Results saved to", output_file)
