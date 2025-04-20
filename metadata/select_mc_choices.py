#!/usr/bin/env python3
import json
import math
import random
import pdb
import geopy.distance
import numpy as np

def select_candidate_indices(turns, path_length):
    """
    Return a list of 3 candidate indices from the path, always including the last or almost last index.
    1. If at least 2 turns are present, take the index before each
       of the last two turns (ensuring a valid non-negative index).
    2. Otherwise, choose 2 indices that are well spaced out along the path.
    """
    candidate_indices = [path_length - random.randint(1, 4)]  # Always include near the last index.
    if len(turns) >= 1:
        # For each turn, take the index immediately before the turn.
        for turn in turns[::-1]:
            # turn is [index, direction] – subtract 1 to get the preceding index.
            idx = turn[0] - 1
            if idx < 0:
                idx = 0
            if idx + 1 not in candidate_indices:
                # Ensure we don't add adjacent indices.
                candidate_indices.append(idx)
    else:
        candidate_indices += [int(round(x)) for x in
                             [path_length * 0.33, path_length * 0.66]]
    # Ensure we have three unique indices; if duplicates occur or we still have fewer than 3, add random ones.
    candidate_indices = list(dict.fromkeys(candidate_indices))  # remove duplicates while preserving order
    candidate_indices.sort()
    print(f"Candidate indices: {candidate_indices}")
    while len(candidate_indices) < 3:
        segments = [idx - candidate_indices[i-1] if i > 0 else idx for i, idx in enumerate(candidate_indices)]
        longest_segment_i = np.argmax(segments)
        lower_bound = candidate_indices[longest_segment_i-1] if longest_segment_i > 0 else 0
        upper_bound = candidate_indices[longest_segment_i]
        print(f"Path length: {path_length}, Segments: {segments}, Lower bound: {lower_bound}, Upper bound: {upper_bound}")
        new_idx = random.randint(lower_bound+5, upper_bound-4)
        if new_idx not in candidate_indices:
            # Ensure we don't add adjacent indices.
            print(f"Adding new index to candidate_indices: {new_idx}")
            candidate_indices.append(new_idx)
            candidate_indices.sort()
    # In case there are more than 3, select the last 3.
    candidate_indices = candidate_indices[-3:]
    return candidate_indices

def compute_multiple_choice_positions(route):
    """
    Given a route object with 'turns' and 'path', create a new field
    "multiple_choice_positions" which is a list of 3 positions (randomly labeled 1,2,3)
    with computed pairwise distances.
    """
    path = route.get("path", [])
    turns = route.get("turns", [])
    if len(path) < 20:
        return None

    # Determine candidate indices
    candidate_indices = select_candidate_indices(turns, len(path))
    # Randomly shuffle the candidate indices to assign labels arbitrarily.
    random.shuffle(candidate_indices)

    # Extract the candidate positions from the path.
    candidates = []
    for idx in candidate_indices:
        candidates.append(path[idx])

    # Create the multiple_choice_positions list.
    # Each candidate gets a label (mc_num: 1,2,3) and computed distances.
    mc_positions = []
    for i, candidate in enumerate(candidates):
        pos = {
            "pano_id": candidate.get("pano_id"),
            "lat": candidate.get("lat"),
            "lng": candidate.get("lng"),
            "pano_lat": candidate.get("pano_lat"),
            "pano_lng": candidate.get("pano_lng"),
            "mc_num": i + 1,
            "idx": candidate.get("idx"),
            "landmarks": (None, None)
        }
        mc_positions.append(pos)

    # Add the new field to the route.
    route["multiple_choice_positions"] = mc_positions
    return route

def process_routes(input_filename, output_filename):
    # Load the input JSON.
    with open(input_filename, "r") as infile:
        data = json.load(infile)
    
    # Expecting data to be a list of routes.
    processed_routes = []
    for route in data:
        new_route = compute_multiple_choice_positions(route)
        if new_route:
            processed_routes.append(new_route)
        else:
            print(f"Route with insufficient path length skipped: {route.get('route_id', 'unknown')}, len= {len(route.get('path', []))}")
    
    # Write the updated data to the output file.
    with open(output_filename, "w") as outfile:
        json.dump(processed_routes, outfile, indent=2)
    print(f"Processed {len(processed_routes)} routes. Output written to {output_filename}")

if __name__ == "__main__":
    input_file = "../data/test_positions_easy_processed_mapped_v2.json"
    output_file = "../data/test_positions_easy_processed_mapped_answered_v2.json"
    process_routes(input_file, output_file)
