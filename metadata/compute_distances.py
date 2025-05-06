import os
import json
from geopy.distance import geodesic

def compute_path_distances(path):
    """
    Given a list of dicts each containing 'lat' and 'lng', compute:
      - distance_to_next and distance_to_prev (meters) for each element
      - a cumulative_distance list: distance along the path from the first point
    Returns:
      cumulative: list of same length, cumulative[i] = distance from idx=0 to idx=i
    """
    n = len(path)
    # compute segment distances
    seg_dists = [0.0] * (n - 1)
    for i in range(n - 1):
        p1 = (path[i]['pano_lat'], path[i]['pano_lng'])
        p2 = (path[i+1]['pano_lat'], path[i+1]['pano_lng'])
        seg_dists[i] = geodesic(p1, p2).meters

    # cumulative distances
    cumulative = [0.0] * n
    for i in range(1, n):
        cumulative[i] = cumulative[i-1] + seg_dists[i-1]

    # assign distance_to_next and distance_to_prev
    for i in range(n):
        path[i]['distance_to_prev'] = cumulative[i] - cumulative[i-1] if i > 0 else None
        path[i]['distance_to_next'] = seg_dists[i] if i < n-1 else None

    return cumulative

def update_multiple_choice(mcp_list, cumulative):
    """
    Given multiple_choice_positions list and the cumulative path distances,
    replace distance_from_x keys by distance_to_{mc_num} computed along path.
    Assumes each item has 'mc_num' and 'idx' (index into path).
    """
    # build map from mc_num to idx
    mc_map = { item['mc_num']: item['idx'] for item in mcp_list }
    # for each item
    for item in mcp_list:
        i_mc = item['mc_num']
        i_idx = item['idx']

        # compute new distances
        for j_mc, j_idx in mc_map.items():
            if j_mc == i_mc:
                continue
            dist = abs(cumulative[j_idx] - cumulative[i_idx])
            item[f'distance_to_{j_mc}'] = dist

def process_json(input_path: str, output_path: str) -> None:
    data = json.load(open(input_path))
    for route in data:
        path = route.get('path', [])
        if not path:
            continue
        # 1) compute path distances
        cumulative = compute_path_distances(path)
        # 2) update multiple_choice_positions
        mcp = route.get('multiple_choice_positions', [])
        if mcp:
            update_multiple_choice(mcp, cumulative)
    # write out
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Add path and along-path distances to JSON routes")
    # p.add_argument("--input_json", default="test_positions_easy_processed_mapped_answered_v2.json", help="Input JSON file")
    # p.add_argument("--output_json", default="test_positions_easy_processed_mapped_answered_redistanced_v2.json", help="Output JSON file")
    p.add_argument("--input_json", default="../data/train_positions_processed_mapped_v2.json", help="Input JSON file")
    p.add_argument("--output_json", default="../data/train_positions_processed_mapped_redistanced_v2.json", help="Output JSON file")
    args = p.parse_args()
    process_json(args.input_json, args.output_json)
