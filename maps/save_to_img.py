import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep

def html_to_image(html_file, override = False):
    """Converts an HTML file to an image using Selenium and Chrome.

    Args:
        html_file (str): Path to the HTML file.
    """
    screenshot_file = os.path.splitext(html_file)[0] + ".png"
    if not override and os.path.exists(screenshot_file):
        return

    # Set up Chrome WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    # Load the HTML file
    driver.get(f"file:///{os.path.abspath(html_file)}")

    # Wait for the page to load
    sleep(5)
    # Get the screenshot
    driver.save_screenshot(screenshot_file)
    print("Saved image to ", screenshot_file)

    # Close the browser
    driver.quit()

# Get the current directory
current_dir = os.getcwd()

# Iterate through HTML files in the directory
for file in os.listdir(current_dir):
    if file.endswith(".html"):
        html_file_path = os.path.join(current_dir, file)
        html_to_image(html_file_path)