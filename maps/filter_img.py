import os
import cv2
import numpy as np
from PIL import Image
import pytesseract

# Set the path to the Tesseract executable if needed
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def is_mostly_grey(image_path):
    # Open the image and convert to grayscale
    image = cv2.imread(image_path)
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Calculate the percentage of the image that is close to grey
    mean_value = np.mean(gray_image)
    
    # If mean value is close to 128, we assume the image is grey
    # You can adjust this threshold as necessary
    grey_threshold = 128
    return abs(mean_value - grey_threshold) < 20

def contains_oops_text(image_path):
    # Open the image using Pillow
    image = Image.open(image_path)

    # Use pytesseract to extract text
    extracted_text = pytesseract.image_to_string(image)

    # Check if the text "oops something went wrong" is in the extracted text
    if "Oops! Something went wrong." in extracted_text:
        return True
    if "This page didn't load Google Maps correctly." in extracted_text:
        return True
    if "See the JavaScript console for technical details." in extracted_text:
        return True
    return False

def process_images(image_folder):
    # List all files in the folder
    files = os.listdir(image_folder)
    image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    # Check each image
    for image_file in image_files:
        image_path = os.path.join(image_folder, image_file)
        
        if is_mostly_grey(image_path):
            print(f"Image {image_file} is mostly grey.")
        
        if contains_oops_text(image_path):
            print(f"Image {image_file} contains 'oops! something went wrong'.")

# Example usage:
image_folder = "/data/claireji/maps/test_maps/"  # Replace with your folder path
process_images(image_folder)
