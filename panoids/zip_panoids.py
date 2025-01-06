import json
import os
import zipfile

# Function to zip jpg files for the first 60 dictionaries
def zip_thumbnails(json_file, thumbnails_folder, output_zip):
    # Load the JSON data
    with open(json_file, 'r') as f:
        test_positions = json.load(f)

    # Create a list to store the files to zip
    files_to_zip = set()

    # Process the first 60 dictionaries in the JSON
    for entry in test_positions:
        route_panoids = entry.get("image_list", [])

        for panoid in route_panoids:
            # Construct the jpg file path
            jpg_file = os.path.join(thumbnails_folder, f"{panoid}.jpg")

            # Check if the file exists before adding
            if os.path.exists(jpg_file):
                files_to_zip.add(jpg_file)

    # Create the zip file
    with zipfile.ZipFile(output_zip, 'w') as zipf:
        for file in files_to_zip:
            zipf.write(file, os.path.basename(file))

    print(f"Zipped {len(files_to_zip)} files into {output_zip}")

# Specify file paths
json_file = '../data/test_positions_augmented_mapped.json'  # Replace with your JSON file path
thumbnails_folder = '/data/claireji/thumbnails/'  # Replace with your thumbnails folder path
output_zip = 'thumbnails.zip'  # Replace with your desired output zip file path

# Zip the thumbnails
zip_thumbnails(json_file, thumbnails_folder, output_zip)
