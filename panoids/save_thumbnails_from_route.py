import json
import requests
import os
import sys
import time
import hashlib
import hmac
import base64
import urllib.parse as urlparse

OVERRIDE = False

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

def download_street_view_thumbnail(pano_id, yaw=0, heading=0, fov=120, image_folder="/data/claireji/thumbnails/"):
    """
    Download Street View thumbnail for the given panoId.

    Parameters:
    - pano_id: The panoId for the Street View image.
    - yaw: Camera yaw angle.
    - heading: Camera heading angle.
    - fov: Field of view in degrees.
    - image_folder: Directory to save the image.
    """
    os.makedirs(image_folder, exist_ok=True)
    image_path = os.path.join(image_folder, f"{pano_id}_{heading}.jpg")

    if os.path.exists(image_path) and not OVERRIDE:
        print(f"Thumbnail for {pano_id}_{heading} already exists.")
        return

    url = (
        f"https://tile.googleapis.com/v1/streetview/thumbnail?"
        f"session={session_key}&key={api_key}"
        f"&panoId={pano_id}&height=250&width=600"
        f"&pitch=0&yaw={heading}&fov={fov}&heading={heading}"
    )
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(image_path, "wb") as f:
            for chunk in response:
                f.write(chunk)
        print(f"Downloaded thumbnail for panoId {pano_id} at {image_path}")
    else:
        print(f"Failed to download thumbnail for panoId {pano_id} with status {response.status_code}")

def process_route_images(route, image_folder):
    """
    Process each route to fetch metadata and download thumbnails.

    Parameters:
    - route: A route dictionary containing 'lat_lng_path' and 'route_panoids'.
    - image_folder: Directory to save thumbnail images.
    """
    assert len(route['image_list']) == len(route['route_panoids']), "Mismatch between image_list and route_panoids length."
    for i, panoid in enumerate(route['image_list']):
        heading = panoid.split("_")[-1]
        pano_id = route['route_panoids'][i]

        download_street_view_thumbnail(pano_id, heading=heading, image_folder=image_folder)
        time.sleep(0.1)

if __name__ == "__main__":
    # Load the graph and routes from JSON files
    split = "test"

    with open(f"../data/{split}_positions_easy_mapped.json", "r") as f:
        routes = json.load(f)

    # Create folders for saving metadata and images
    image_folder = f"/data/claireji/thumbnails/"

    # Process each route
    for idx, route in enumerate(routes[:200]):
        process_route_images(route, image_folder)