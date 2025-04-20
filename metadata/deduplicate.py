import json

file_path = '../data/test_positions_augmented.json'  
write_file_path = '../data/test_positions_augmented_consolidated.json'
with open(file_path, 'r') as file:
    positions = json.load(file)

def remove_consecutive_repeats(lst):
    idx_kept = [0]
    idx = 0
    if not lst:
        return lst  # Handle empty list case
    result = [lst[0]]  # Start with the first element
    for i,item in enumerate(lst[1:]):
        if item != result[-1]:  # Add only if different from the last added item
            result.append(item)
            idx += 1
            idx_kept.append(i+1)
    return result, idx_kept

def process_mapping(lst, mapping):
    result = []
    for i,item in enumerate(lst):
        if i in mapping:
            result.append(item)
    return result

for route in positions:
    route['lat_lng_path'], mapping = remove_consecutive_repeats(route['lat_lng_path'])
    route['route_panoids'] = process_mapping(route['route_panoids'], mapping)
    del route['ground_truth_position']
    del route['multiple_choice_positions']

with open(write_file_path, 'w') as file:
    json.dump(positions, file, indent=4)
