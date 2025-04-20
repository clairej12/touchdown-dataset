import json
import math

# def smooth_headings(headings, window_size=5):
#     """
#     Smooths a list of headings (in degrees) using a circular moving average.
#     window_size should be an odd number for a symmetric window.
#     Returns a list of smoothed headings.
#     """
#     n = len(headings)
#     smoothed = []
#     for i in range(n):
#         # Define window limits
#         start = max(0, i - window_size // 2)
#         end = min(n, i + window_size // 2 + 1)
#         window = headings[start:end]
#         sin_sum = sum(math.sin(math.radians(h)) for h in window)
#         cos_sum = sum(math.cos(math.radians(h)) for h in window)
#         avg_heading = math.degrees(math.atan2(sin_sum, cos_sum)) % 360
#         smoothed.append(round(avg_heading, 2))
#     return smoothed

# def apply_smoothing(positions):
#     headings = [pos["pano_heading"] for pos in positions["path"]]
#     smoothed_headings = smooth_headings(headings)
#     for i in range(len(positions)):
#         positions["path"][i]["pano_heading"] = smoothed_headings[i]
    
# file = "../data/test_positions_easy_processed_mapped_v2.json"
# with open(file, "r") as infile:
#     data = json.load(infile)
# for route in data:
#     apply_smoothing(route)
# with open(file, "w") as outfile:
#     json.dump(data, outfile, indent=2)
# print(f"Processed {len(data)} routes. Output written to {file}")

up_to_date_file = "../data/test_positions_easy_processed_mapped_v2.json"
out_of_date_file = "../data/test_positions_easy_processed_mapped_answered_v2.json"
with open(up_to_date_file, "r") as infile:
    data = json.load(infile)
with open(out_of_date_file, "r") as infile:
    data2 = json.load(infile)
for route in data2:
    route_id = route["route_id"]
    found = False
    for r in data:
        if r["route_id"] == route_id:
            route["path"] = r["path"]
            for i, entry in enumerate(route["path"]):
                entry["idx"] = i
            found = True
            break
    if not found:
        del data2[route_id]
with open(out_of_date_file, "w") as outfile:
    json.dump(data2, outfile, indent=2)
print(f"Processed {len(data2)} routes. Output written to {out_of_date_file}")