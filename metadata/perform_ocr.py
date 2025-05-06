import os
import json
from PIL import Image
import pytesseract
import requests
import base64
from tqdm import tqdm
import pdb

# Adjust this path to your input file
INPUT_JSON_FILE = "../../data-collection/test_positions_easy_processed_mapped_answered_redistanced_v2.json"
OUTPUT_JSON_FILE = "../data/test_positions_easy_processed_mapped_answered_redistanced_ocr_v2.json"
IMAGES_DIR = "../../data-collection/thumbnails_sharpened/"  # directory where your JPGs are stored

API_KEY = os.getenv("GOOGLE_VISION_API_KEY")

if not API_KEY:
    raise ValueError("Please set the GOOGLE_VISION_API_KEY environment variable.")
# Set the path to the Tesseract OCR executable
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Adjust this path if needed

def google_ocr(image_path):
    # Read and encode the image as base64
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    # Prepare the payload for the Vision API
    payload = {
        "requests": [
            {
                "image": {"content": encoded_image},
                "features": [{"type": "TEXT_DETECTION"}],
            }
        ]
    }

    # Make the POST request to the Vision API
    url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
    response = requests.post(url, json=payload)

    # Check and parse the response
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        return ""

    result = response.json()
    pdb.set_trace()
    try:
        return result["responses"][0]["textAnnotations"][0]["description"]
    except (KeyError, IndexError):
        print(f"No text detected in {image_path}")
        return ""

def pytesseract_ocr(filename):
    """Run OCR on the given image file and return extracted text."""
    try:
        with Image.open(filename) as img:
            text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return ""

def process_routes(routes):
    """Add OCR text to each path entry in the routes list."""
    for route in tqdm(routes):
        for step in route.get("path", []):
            pano_id = step["pano_id"]
            pano_heading = step["pano_heading"]
            image_filename = os.path.join(IMAGES_DIR, f"{pano_id}_{pano_heading}_sharpened.jpg")

            if not os.path.exists(image_filename):
                print(f"Image file not found: {image_filename}")
                continue
            
            print(f"Processing image: {image_filename}")
            # Perform OCR using both methods
            pytesseract_ocr_text = pytesseract_ocr(image_filename)
            step["pytesseract_ocr_text"] = pytesseract_ocr_text
            google_ocr_text = google_ocr(image_filename)
            step["google_ocr_text"] = google_ocr_text

    return routes

def main():
    # Load input JSON
    with open(INPUT_JSON_FILE, "r") as f:
        routes = json.load(f)

    # Process with OCR
    updated_routes = process_routes(routes)

    # Save output JSON
    with open(OUTPUT_JSON_FILE, "w") as f:
        json.dump(updated_routes, f, indent=2)

    print(f"OCR results saved to: {OUTPUT_JSON_FILE}")

if __name__ == "__main__":
    main()
