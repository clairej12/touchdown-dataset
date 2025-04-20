import json
import requests
import os
import sys
import time
import hashlib
import hmac
import base64
import urllib.parse as urlparse
import pdb

# Load API key
api_key = os.getenv("MAPS_API_KEY")
if api_key is None:
    raise ValueError("API key not found. Please set the MAPS_API_KEY environment variable.")
else:
    print("API key loaded successfully.")

# Session key for tile.googleapis requests
url = f"https://tile.googleapis.com/v1/createSession?key={api_key}"
headers = {
    "Content-Type": "application/json"
}
payload = {
    "mapType": "streetview",
    "language": "en-US",
    "region": "US"
}

try:
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # Raise an error for bad status codes
    data = response.json()
    session_key = data.get("session")
    if session_key:
        print(f"Session Key: {session_key}")
    else:
        raise ValueError("Failed to retrieve session key.")
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
    raise ValueError("Session key failed to be retrieved.")

signature = os.getenv("MAPS_URL_SIGNATURE")
if signature is None:
    raise ValueError("URL signature not found. Please set the MAPS_URL_SIGNATURE environment variable.")
else:
    print("URL signature loaded successfully.")

def fetch_metadata(lat, lng, metadata_folder, radius = 20):
    """
    Fetch Street View metadata for the given latitude and longitude.

    Parameters:
    - lat: Latitude of the location.
    - lng: Longitude of the location.
    - radius: Search radius in meters.

    Returns:
    - Metadata response as a dictionary.
    """
    url = (
        f"https://maps.googleapis.com/maps/api/streetview/metadata?"
        f"key={api_key}&location={lat},{lng}&source=outdoor"
    )

    signing_url = urlparse.urlparse(url)
    url_to_sign = signing_url.path + "?" + signing_url.query

    # Decode the private key into its binary format
    # We need to decode the URL-encoded private key
    decoded_key = base64.urlsafe_b64decode(signature)

    # Create a signature using the private key and the URL-encoded
    # string using HMAC SHA1. This signature will be binary.
    url_signature = hmac.new(decoded_key, str.encode(url_to_sign), hashlib.sha1)

    # Encode the binary signature into base64 for use within a URL
    encoded_signature = base64.urlsafe_b64encode(url_signature.digest())

    url = url + "&signature=" + encoded_signature.decode("utf-8")
    
    response = requests.get(url)
    if response.status_code == 200:
        sv_metadata = response.json()
    else:
        print(f"Failed to fetch metadata for {lat}, {lng} with status {response.status_code}")
        sv_metadata = None
    
    pano_id = sv_metadata.get("pano_id") if sv_metadata and "status" in sv_metadata else None

    metadata_path = os.path.join(metadata_folder, f"{pano_id}.json")
    if os.path.exists(metadata_path):
        # print(f"Metadata for panoId {pano_id} already exists.")
        return sv_metadata

    if pano_id:
        url = (f"https://tile.googleapis.com/v1/streetview/metadata?"
               f"session={session_key}&key={api_key}&panoId={pano_id}")
    else:
        url = (
            f"https://tile.googleapis.com/v1/streetview/metadata?"
            f"session={session_key}&key={api_key}&lat={lat}&lng={lng}&radius={radius}"
        )
    response = requests.get(url)
    if response.status_code == 200:
        metadata = response.json()
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"Saved metadata for panoId {pano_id} at {metadata_path}")
        return metadata
    else:
        pdb.set_trace()
        print(f"Failed to fetch metadata for {lat}, {lng} with status {response.status_code}")
        
def process_route_metadata(route, metadata_folder, panoid_mapping):
    """
    Process each route to fetch metadata and download thumbnails.

    Parameters:
    - route: A route dictionary containing 'lat_lng_path' and 'route_panoids'.
    - metadata_folder: Directory to save metadata files.
    - image_folder: Directory to save thumbnail images.
    """
    os.makedirs(metadata_folder, exist_ok=True)

    for i, panoid in enumerate(route['route_panoids']):
        lat,lng = route['lat_lng_path'][i]

        # Fetch metadata for the node's coordinates
        if panoid not in panoid_mapping:
            metadata = fetch_metadata(lat, lng, metadata_folder)
            if metadata and ("panoId" in metadata or "pano_id" in metadata):
                pano_id = metadata["panoId"] if "panoId" in metadata else metadata["pano_id"]
                panoid_mapping[panoid] = pano_id
            else:
                print(f"Metadata not available for {lat,lng}")
        else:
            print(f"Metadata for {panoid} already exists.")

        time.sleep(0.1)
    return panoid_mapping

if __name__ == "__main__":
    # Load the graph and routes from JSON files
    split = "test"
    with open(f"../data/{split}_positions_easy.json", "r") as f:
        routes = json.load(f)

    # Create folders for saving metadata and images
    metadata_folder = f"/data/claireji/panoid_metadata/"

    with open(f"../metadata/{split}_panoid_mapping.json", "r") as f:
        panoid_mapping = json.load(f)

    # Process each route
    for idx, route in enumerate(routes[:60]):
        mapping = process_route_metadata(route, metadata_folder, panoid_mapping)
        panoid_mapping.update(mapping)
    
    # Save the panoid mapping to a JSON file
    with open(f"../metadata/{split}_easy_panoid_mapping.json", "w") as f:
        json.dump(panoid_mapping, f, indent=2)
