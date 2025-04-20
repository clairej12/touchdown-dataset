import json
import requests
import os
import time
import hashlib
import hmac
import base64
import urllib.parse as urlparse
import pdb
import math

# Configuration
OVERRIDE = True
OVERRIDE_METADATA = False
OVERRIDE_IMAGES = True
API_KEY = os.getenv("MAPS_API_KEY")
SIGNATURE = os.getenv("MAPS_URL_SIGNATURE")
IMAGE_FOLDER = "/data/claireji/thumbnails/"
METADATA_FOLDER = "/data/claireji/panoid_metadata/"
REQUEST_DELAY = 0.1  # To avoid hitting API limits

# Ensure API credentials are available
if not API_KEY or not SIGNATURE:
    raise ValueError("API key or URL signature not found. Set the environment variables.")

# Compute heading for Google Maps
def calculate_bearing(pos1, pos2):
    import math
    lat1, lon1, lat2, lon2 = map(math.radians, [*pos1, *pos2])
    
    delta_lon = lon2 - lon1
    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def compute_average_bearing(pos, subsequent_positions, window_size=3):
    """
    Given the current position `pos` and a list of subsequent positions,
    compute the circular (angular) mean of the bearings from pos to each of the next few points.
    """
    import math
    bearings = []
    for i in range(min(window_size, len(subsequent_positions))):
        bearing = calculate_bearing(pos, subsequent_positions[i])
        bearings.append(bearing)
    if not bearings:
        return 0
    sin_sum = sum(math.sin(math.radians(b)) for b in bearings)
    cos_sum = sum(math.cos(math.radians(b)) for b in bearings)
    avg = math.degrees(math.atan2(sin_sum, cos_sum)) % 360
    return avg

def smooth_headings(headings, window_size=5):
    """
    Smooths a list of headings (in degrees) using a circular moving average.
    window_size should be an odd number for a symmetric window.
    Returns a list of smoothed headings.
    """
    n = len(headings)
    smoothed = []
    for i in range(n):
        # Define window limits
        start = max(0, i - window_size // 2)
        end = min(n, i + window_size // 2 + 1)
        window = headings[start:end]
        sin_sum = sum(math.sin(math.radians(h)) for h in window)
        cos_sum = sum(math.cos(math.radians(h)) for h in window)
        avg_heading = math.degrees(math.atan2(sin_sum, cos_sum)) % 360
        smoothed.append(avg_heading)
    return smoothed

def circular_diff(a, b):
    """Return the smallest difference between two angles (in degrees)."""
    return min((a - b) % 360, (b - a) % 360)

def adjust_heading(computed_heading, next_panoid, metadata):
    """
    If metadata contains 'links', choose the heading in the links that is closest
    to the computed_heading. Otherwise, return computed_heading.
    """
    # # (Optional compare the computed heading to the panorama's default (metadata) heading.
    # default_heading = metadata.get("heading", computed_heading)
    # # If the difference is large (e.g., more than 90°), assume the computed heading might be reversed.
    # if abs(circular_diff(computed_heading, default_heading)) > 90:
    #     # Reverse the computed heading
    #     print(f"Reversing computed heading from {computed_heading} based on {default_heading}")
    #     computed_heading = (computed_heading + 180) % 360

    links = metadata.get("links", [])
    if not links:
        return computed_heading
    
    # Search for matching links
    matching_links = [l for l in links if l.get("panoId") == next_panoid]
    if not matching_links:
        print(f"No matching links found for {next_panoid}. Using computed heading.")
        return computed_heading
    else:
        print(f"Using matching link for {next_panoid} with heading {matching_links[0].get('heading', None)}")
        return matching_links[0].get("heading", computed_heading)

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
def fetch_metadata(lat, lng, total_tile_metadata, radius=20):
    filename1 = f"{lat}_{lng}.json"
    if os.path.exists(os.path.join(METADATA_FOLDER, filename1)) and not OVERRIDE_METADATA:
        with open(os.path.join(METADATA_FOLDER, filename1), "r") as f:
            metadata1 = json.load(f)
    else:
        print(f"Requesting: {filename1}")
        # Check for metadata using the Google Maps API
        url = f"https://maps.googleapis.com/maps/api/streetview/metadata?key={API_KEY}&location={lat},{lng}&source=outdoor"
        url = sign_url(url)

        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch metadata for {lat}, {lng}")
            return None, None

        metadata1 = response.json()

        if metadata1.get("status") == "OK":
            with open(os.path.join(METADATA_FOLDER, filename1), "w") as f:
                json.dump(metadata1, f, indent=2)
            print(f"Metadata saved for {lat}, {lng}")
        else:
            print(f"Metadata fetch failed: {metadata1.get('status')}")
            return None, None
    
    pano_id = metadata1.get("pano_id")
    filename2 = f"{pano_id}.json"
    if pano_id in total_tile_metadata and not OVERRIDE_METADATA:
        metadata2 = total_tile_metadata[pano_id]
    elif os.path.exists(os.path.join(METADATA_FOLDER, filename2)) and not OVERRIDE_METADATA:
        with open(os.path.join(METADATA_FOLDER, filename2), "r") as f:
            metadata2 = json.load(f)
    else:
        print(f"Requesting: {filename2}")
        url = (f"https://tile.googleapis.com/v1/streetview/metadata?"
               f"session={SESSION_KEY}&key={API_KEY}&panoId={pano_id}")
    
        response = requests.get(url)

        if response.status_code == 200:
            metadata2 = response.json()
            with open(os.path.join(METADATA_FOLDER, filename2), "w") as f:
                json.dump(metadata2, f, indent=2)
            print(f"Metadata tile saved for {lat}, {lng}")
        else:
            print(f"Failed to fetch lat/lng metadata (HTTP {response.status_code})")
            return None, None

    return metadata1, metadata2

# Process positions and remove duplicates
def process_route(route, total_metadata = {}, total_tile_metadata = {}):
    positions = route["lat_lng_path"]
    headings = route["headings"]
    processed_positions = []  # List to store {pano_id, lat, lng, heading}
    
    last_pano_id = None  # Track last unique pano_id
    last_position = None  # Track last used position for heading calculation

    for i in range(len(positions) - 1):
        lat1, lng1 = positions[i]
        lat2, lng2 = positions[i + 1]

        # Fetch metadata once per position
        metadata, metadata_tile = fetch_metadata(lat1, lng1, total_tile_metadata)
        if not metadata:
            print(f"Metadata not found for {lat1}, {lng1}")
            continue
        # Extract pano_id from metadata
        pano_id1 = metadata.get("pano_id")
        location = metadata.get("location")
        pano_lat = location.get("lat", lat1)
        pano_lng = location.get("lng", lng1)
        print(f"Processing {i + 1}/{len(positions)}: {lat1}, {lng1}, {pano_id1} -> {lat2}, {lng2}")

        # Save metadata for the current position
        if pano_id1 not in total_metadata:
            total_metadata[pano_id1] = metadata
        if pano_id1 not in total_tile_metadata:
            total_tile_metadata[pano_id1] = metadata_tile

        # Only add pano_id1 if it's not the same as the last added pano_id
        if pano_id1 and pano_id1 != last_pano_id:
            processed_positions.append({"pano_id": pano_id1, 
                                        "lat": lat1, "lng": lng1, "heading": headings[i],
                                        "pano_lat": pano_lat, "pano_lng": pano_lng,
                                        })

            last_pano_id = pano_id1
            last_position = (pano_lat, pano_lng)

        time.sleep(REQUEST_DELAY)

    # Add the last position if it's unique
    metadata, metadata_tile = fetch_metadata(lat2, lng2, total_tile_metadata)
    if not metadata:
        print(f"Metadata not found for {lat2}, {lng2}")
        return
    pano_id2 = metadata.get("pano_id")
    location = metadata.get("location")
    pano_lat = location.get("lat", lat2)
    pano_lng = location.get("lng", lng2)
    if pano_id2 and pano_id2 != last_pano_id:
        processed_positions.append({"pano_id": pano_id2, 
                                    "lat": lat2, "lng": lng2, "heading": route["headings"][-1],
                                    "pano_lat": pano_lat, "pano_lng": pano_lng})
    # Save metadata for the current position
    if pano_id2 not in total_metadata:
        total_metadata[pano_id2] = metadata
    if pano_id2 not in total_tile_metadata:
        total_tile_metadata[pano_id2] = metadata_tile

    # Calculate heading for each position
    for i in range(len(processed_positions) - 1):
        pos1 = (processed_positions[i]["pano_lat"], processed_positions[i]["pano_lng"])
        subsequent_positions = [(p["pano_lat"], p["pano_lng"]) for p in processed_positions[i+1:]]
        computed_heading = compute_average_bearing(pos1, subsequent_positions, window_size=3)
        processed_positions[i]["pano_heading"] = computed_heading
    processed_positions[-1]["pano_heading"] = processed_positions[-2]["pano_heading"]

    # Snap heading based on metadata
    for i in range(len(processed_positions) - 1):
        current_pano_id = processed_positions[i]["pano_id"]
        next_pano_id = processed_positions[i + 1]["pano_id"]
        # Fetch cached metadata for the next pano_id
        metadata_tile = total_tile_metadata.get(current_pano_id)
        # Adjust heading using metadata
        adjusted_heading = adjust_heading(processed_positions[i]["pano_heading"], next_pano_id, metadata_tile)
        processed_positions[i]["pano_heading"] = adjusted_heading

    # Smooth headings
    headings = [pos["pano_heading"] for pos in processed_positions]
    smoothed_headings = smooth_headings(headings, window_size=3)
    for i in range(len(processed_positions)):
        processed_positions[i]["pano_heading"] = smoothed_headings[i]

    # Round headings
    for i in range(len(processed_positions)):
        processed_positions[i]["pano_heading"] = round(processed_positions[i]["pano_heading"], 2)
    
    # Remove unnecessary fields
    del route["headings"]
    del route["lat_lng_path"]
    route["path"] = processed_positions

    return total_metadata, total_tile_metadata

def process_positions(input_json, output_json, cutoff=100):
    total_metadata = {}
    total_tile_metadata = {}
    with open(input_json, "r") as f:
        routes = json.load(f)
        routes = routes[:cutoff] if cutoff else routes
        print(f"Processing {len(routes)} routes.")
    
    route_ids = set()
    
    if os.path.exists(output_json) and not OVERRIDE:
        existing_data = json.load(open(output_json, "r"))
        route_ids = {r["route_id"] for r in existing_data if "path" in r}
        routes = existing_data
        print(f"Loaded {len(routes)}, {len(routes) - len(route_ids)} of which need to be processed.")

    for i, route in enumerate(routes):
        if route["route_id"] in route_ids:
            continue

        metadata, metadata_tile = process_route(route)
        total_metadata.update(metadata)
        total_tile_metadata.update(metadata_tile)
        
        if i % 5 == 0:
            with open(output_json, "w") as f:
                json.dump(routes, f, indent=2)
            if OVERRIDE_METADATA or not os.path.exists("../metadata/panoid_metadata.json"):
                with open("../metadata/panoid_metadata.json", "w") as f:
                    json.dump(total_metadata, f, indent=2)
            if OVERRIDE_METADATA or not os.path.exists("../metadata/panoid_metadata_tile.json"):
                with open("../metadata/panoid_metadata_tile.json", "w") as f:
                    json.dump(total_tile_metadata, f, indent=2)
        
    # Save cleaned data
    with open(output_json, "w") as f:
        json.dump(routes, f, indent=2)

    print(f"Saved deduplicated positions to {output_json}")

# Download Street View thumbnail
def download_street_view_thumbnail(pano_id, heading, fov=120):
    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    image_path = os.path.join(IMAGE_FOLDER, f"{pano_id}_{heading}.jpg")

    if os.path.exists(image_path) and not OVERRIDE_IMAGES:
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
        heading = entry["pano_heading"]
        download_street_view_thumbnail(pano_id, heading)
        time.sleep(REQUEST_DELAY)

def process_positions_images(input_json):
    with open(input_json, "r") as f:
        data = json.load(f)

    for route in data[:100]:
        process_route_images(route)

# Main execution
if __name__ == "__main__":
    INPUT_JSON = "../data/test_positions_easy_processed.json"
    OUTPUT_JSON = "../data/test_positions_easy_processed_mapped_v2.json"

    process_positions(INPUT_JSON, OUTPUT_JSON, cutoff=65)
    process_positions_images(OUTPUT_JSON)
