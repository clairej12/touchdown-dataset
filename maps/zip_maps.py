import json
import os
import zipfile

# Function to zip jpg files
def zip_maps(json_file, maps_folder, output_zip):
    # Load the JSON data
    with open(json_file, 'r') as f:
        test_positions = json.load(f)

    # Create a list to store the files to zip
    files_to_zip = set()

    # Process the first 60 dictionaries in the JSON
    for entry in test_positions:
        route_id = entry.get("route_id", "")

        png_file = os.path.join(maps_folder, f"test_easy_processed_maps_{route_id}.png")
        if os.path.exists(png_file):
            # Add the png file to the set
            files_to_zip.add(png_file)
        else:
            print(f"File not found: {png_file}")

    # Create the zip file
    with zipfile.ZipFile(output_zip, 'w') as zipf:
        for file in files_to_zip:
            zipf.write(file, os.path.basename(file))

    print(f"Zipped {len(files_to_zip)} files into {output_zip}")

# Specify file paths
json_file = '../data/test_positions_easy_processed_mapped_answered_v2.json'  # Replace with your JSON file path
maps_folder = '/data/claireji/maps/easy_processed_maps_v2/'  # Replace with your thumbnails folder path
output_zip = 'maps.zip'  # Replace with your desired output zip file path

# Zip the thumbnails
zip_maps(json_file, maps_folder, output_zip)
