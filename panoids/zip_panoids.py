import json
import os
import zipfile

# Function to zip jpg files
def zip_thumbnails(json_file, thumbnails_folder, output_zip, cutoff=None):
    # Load the JSON data
    with open(json_file, 'r') as f:
        test_positions = json.load(f)
        test_positions = test_positions[:cutoff] if cutoff else test_positions

    # Create a list to store the files to zip
    files_to_zip = set()

    # Process the first 60 dictionaries in the JSON
    for entry in test_positions:
        route_positions = entry.get("path", [])

        for position in route_positions:
            # Construct the jpg file path
            jpg_file = os.path.join(thumbnails_folder, f"{position['pano_id']}_{position['pano_heading']}.jpg")

            # Check if the file exists before adding
            if os.path.exists(jpg_file):
                files_to_zip.add(jpg_file)

    # Create the zip file
    with zipfile.ZipFile(output_zip, 'w') as zipf:
        for file in files_to_zip:
            zipf.write(file, os.path.basename(file))

    print(f"Zipped {len(files_to_zip)} files into {output_zip}")

# Specify file paths
json_file = '../data/test_positions_easy_processed_mapped_v2.json'  # Replace with your JSON file path
thumbnails_folder = '/data/claireji/thumbnails/'  # Replace with your thumbnails folder path
output_zip = 'thumbnails.zip'  # Replace with your desired output zip file path

# Zip the thumbnails
zip_thumbnails(json_file, thumbnails_folder, output_zip, 100)
