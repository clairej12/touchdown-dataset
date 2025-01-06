import json
import matplotlib.pyplot as plt

def analyze_turns(input_file, output_file):
    """
    Reads a JSON file with route data, identifies routes with turns, counts turns, and plots a histogram.

    Args:
        input_file (str): Path to the input JSON file.
        output_file (str): Path to the output file where route IDs will be written.
    """
    routes_with_turns = []
    turn_counts = []

    # Load the input JSON data
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Iterate through each route and analyze turns
    for route in data:
        route_id = route["route_id"]
        directions = route["directions"]

        # Count the number of turns (Left or Right)
        num_turns = sum(1 for d in directions if d["direction"] in ["Left", "Right"])
        
        if num_turns > 0:
            routes_with_turns.append(route_id)
        turn_counts.append(num_turns)

    # Write the route IDs with turns to the output file
    with open(output_file, 'w') as f:
        for route_id in routes_with_turns:
            f.write(f"{route_id}\n")

    print(f"Found {len(routes_with_turns)} routes with at least one turn from {len(data)}. IDs written to {output_file}.")
    print(f"Average number of turns per route: {sum(turn_counts) / len(turn_counts):.2f}")
    print(f"Maximum number of turns in a route: {max(turn_counts)}")
    print(f"Minimum number of turns in a route: {min(turn_counts)}")
    # Plot histogram of turn counts
    plt.figure(figsize=(10, 6))
    plt.hist(turn_counts, bins=range(0, max(turn_counts) + 2), edgecolor="black", align="left")
    plt.title("Distribution of Number of Turns per Route")
    plt.xlabel("Number of Turns")
    plt.ylabel("Frequency")
    plt.xticks(range(0, max(turn_counts) + 1))
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.savefig("turn_counts_histogram.png")

# Specify input and output file paths
input_file = "../metadata/turns.json"  # Replace with your input JSON file
output_file = "../metadata/routes_with_turns.txt"  # Replace with your desired output file

# Run the function
analyze_turns(input_file, output_file)
