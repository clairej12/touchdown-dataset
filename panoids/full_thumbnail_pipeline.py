import json
import requests
import os
import time
import hashlib
import hmac
import base64
import urllib.parse as urlparse

# Configuration
OVERRIDE = False
API_KEY = os.getenv("MAPS_API_KEY")
SIGNATURE = os.getenv("MAPS_URL_SIGNATURE")
IMAGE_FOLDER = "/data/claireji/thumbnails/"
# METADATA_FOLDER = "/data/claireji/panoid_metadata/"
REQUEST_DELAY = 0.1  # To avoid hitting API limits

# Ensure API credentials are available
if not API_KEY or not SIGNATURE:
    raise ValueError("API key or URL signature not found. Set the environment variables.")

# Create Street View session
def create_streetview_session():
    url = f"https://tile.googleapis.com/v1/createSession?key={API_KEY}"
    payload = {"mapType": "streetview", "language": "en-US", "region": "US"}
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    session_key = response.json().get("session")
    if not session_key:
        raise ValueError("Failed to retrieve session key.")
    
    return session_key

SESSION_KEY = create_streetview_session()

# Sign a URL using HMAC-SHA1
def sign_url(url):
    parsed = urlparse.urlparse(url)
    url_to_sign = parsed.path + "?" + parsed.query

    decoded_key = base64.urlsafe_b64decode(SIGNATURE)
    url_signature = hmac.new(decoded_key, url_to_sign.encode(), hashlib.sha1)
    encoded_signature = base64.urlsafe_b64encode(url_signature.digest())

    return f"{url}&signature={encoded_signature.decode()}"

# Fetch Street View metadata
def fetch_metadata(lat, lng, radius=20):
    url = f"https://maps.googleapis.com/maps/api/streetview/metadata?key={API_KEY}&location={lat},{lng}&source=outdoor"
    url = sign_url(url)

    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch metadata for {lat}, {lng}")
        return None

    metadata = response.json()

    if metadata.get("status") == "OK":
        pano_id = metadata.get("pano_id")
        if pano_id:
            return pano_id

    print(f"Defaulting to lat/long search for {lat}, {lng}")
    url = (
        f"https://tile.googleapis.com/v1/streetview/metadata?"
        f"session={SESSION_KEY}&key={API_KEY}&lat={lat}&lng={lng}&radius={radius}"
    )
    response = requests.get(url)

    if response.status_code == 200:
        metadata = response.json()
        if metadata.get("status") == "OK":
            return metadata.get("panoId")
        else:
            print(f"Lat/lng search failed: {metadata.get('status')}")
    else:
        print(f"Failed to fetch lat/lng metadata (HTTP {response.status_code})")

    return None

# Compute heading for Google Maps
def calculate_bearing(pos1, pos2):
    import math
    lat1, lon1, lat2, lon2 = map(math.radians, [*pos1, *pos2])
    
    delta_lon = lon2 - lon1
    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    
    return (math.degrees(math.atan2(x, y)) + 360) % 360

# Process positions and remove duplicates
def process_route(route):
    positions = route["lat_lng_path"]
    processed_positions = []  # List to store {pano_id, lat, lng, heading}
    
    last_pano_id = None  # Track last unique pano_id
    last_position = None  # Track last used position for heading calculation

    for i in range(len(positions) - 1):
        lat1, lng1 = positions[i]
        lat2, lng2 = positions[i + 1]

        # Fetch metadata once per position
        pano_id1 = fetch_metadata(lat1, lng1)
        print(f"Processing {i + 1}/{len(positions)}: {lat1}, {lng1}, {pano_id1} -> {lat2}, {lng2}")

        # Only add pano_id1 if it's not the same as the last added pano_id
        if pano_id1 and pano_id1 != last_pano_id:
            heading = calculate_bearing((lat1, lng1), (lat2, lng2)) 
            processed_positions.append({"pano_id": pano_id1, "lat": lat1, "lng": lng1, "heading": round(heading, 2)})

            last_pano_id = pano_id1
            last_position = (lat1, lng1)

        time.sleep(REQUEST_DELAY)

    # Add the last position if it's unique
    pano_id2 = fetch_metadata(lat2, lng2)
    if pano_id2 and pano_id2 != last_pano_id:
        heading = calculate_bearing(last_position, (lat2, lng2)) if last_position else route["end_heading"]
        processed_positions.append({"pano_id": pano_id2, "lat": lat2, "lng": lng2, "heading": round(heading, 2)})

    del route["headings"]
    del route["lat_lng_path"]
    route["path"] = processed_positions

def process_positions(input_json, output_json):
    with open(input_json, "r") as f:
        routes = json.load(f)
    
    route_ids = set()
    
    if os.path.exists(output_json) and not OVERRIDE:
        existing_data = json.load(open(output_json, "r"))
        route_ids = {r["route_id"] for r in existing_data if "path" in r}
        routes = existing_data
        print(f"Loaded {len(routes)}, {len(routes) - len(route_ids)} of which need to be processed.")

    for i, route in enumerate(routes):
        if route["route_id"] in route_ids:
            continue

        process_route(route)
        
        if i % 5 == 0:
            with open(output_json, "w") as f:
                json.dump(routes, f, indent=2)
        

    # Save cleaned data
    with open(output_json, "w") as f:
        json.dump(routes, f, indent=2)

    print(f"Saved deduplicated positions to {output_json}")

# Download Street View thumbnail
def download_street_view_thumbnail(pano_id, heading, fov=120):
    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    image_path = os.path.join(IMAGE_FOLDER, f"{pano_id}_{heading}.jpg")

    if os.path.exists(image_path) and not OVERRIDE:
        print(f"Skipping: {image_path}")
        return  # Skip existing images

    url = (
        f"https://tile.googleapis.com/v1/streetview/thumbnail?"
        f"session={SESSION_KEY}&key={API_KEY}"
        f"&panoId={pano_id}&height=250&width=600"
        f"&pitch=0&yaw={heading}&fov={fov}&heading={heading}"
    )

    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(image_path, "wb") as f:
            for chunk in response:
                f.write(chunk)
        print(f"Downloaded: {image_path}")
    else:
        print(f"Failed to download image for {pano_id}")

# Process images from deduplicated positions
def process_route_images(route):
    positions = route["path"]

    for entry in positions:
        pano_id = entry["pano_id"]
        heading = entry["heading"]
        download_street_view_thumbnail(pano_id, heading)
        time.sleep(REQUEST_DELAY)

def process_positions_images(input_json):
    with open(input_json, "r") as f:
        data = json.load(f)

    for route in data[:200]:
        process_route_images(route)

# Main execution
if __name__ == "__main__":
    INPUT_JSON = "../data/test_positions_easy_processed.json"
    OUTPUT_JSON = "../data/test_positions_easy_processed_mapped.json"

    # process_positions(INPUT_JSON, OUTPUT_JSON)
    process_positions_images(OUTPUT_JSON)
