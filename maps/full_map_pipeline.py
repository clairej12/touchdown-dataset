import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep
import json
from gmplot import GoogleMapPlotter
import os
from bs4 import BeautifulSoup
import re

# MAP_DIR, PREFIX = '/data/claireji/maps/test_maps/', 'test_maps'
# MAP_DIR, PREFIX = '/data/claireji/maps/zoomed_maps/', 'test_zoomed_maps'
# MAP_DIR, PREFIX = '/data/claireji/maps/easy_processed_maps/', 'test_easy_processed_maps'
# MAP_DIR, PREFIX = '/data/claireji/maps/easy_processed_maps_v2/', 'test_easy_processed_maps'
MAP_DIR, PREFIX = '/data/claireji/maps/easy_processed_maps_v2/', 'train_processed_maps_no_pins'


# Function to modify marker icons and markers
def update_html_markers(file_path, output_path):
    # Read the HTML file
    with open(file_path, 'r') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find all marker icon definitions
    scripts = soup.find_all('script', type='text/javascript')

    for script in scripts:
        script_text = script.string
        if not script_text:
            continue

        # Modify marker icons
        script_text = re.sub(
            r'var marker_icon_(\w+) = \{([^}]+)\};',
            lambda m: f"""var marker_icon_{m.group(1)} = {{\n            url: "{m.group(2).split('",')[0].split('"')[1]}",\n            labelOrigin: new google.maps.Point(20, 20),\n            scaledSize: new google.maps.Size(40, 70)\n        }};""",
            script_text
        )

        # Modify markers
        script_text = re.sub(
            r'new google\.maps\.Marker\(\{([^}]+)\}\);',
            lambda m: re.sub(
                r'label: \"(.*?)\"',
                lambda label_match: f"label: {{\n                text: \"{label_match.group(1)}\",\n                fontSize: \"28px\"\n            }}",
                m.group(0)
            ),
            script_text
        )

        # Update the script text
        script.string.replace_with(script_text)

    # Write the updated HTML to the output file
    with open(output_path, 'w') as file:
        file.write(str(soup))

class CustomGoogleMapPlotter(GoogleMapPlotter):
    def __init__(self, center_lat, center_lng, zoom, apikey='',
                 map_type='satellite', bounds = None):
        super().__init__(center_lat, center_lng, zoom, apikey, map_type)
        self.bounds = bounds
        self.map_type = map_type
        self.apikey = apikey

    def write_map(self,  f):
        f.write('\t\tvar myOptions = {\n')
        f.write('\t\t\tzoom: %d,\n' % (self.zoom))
        f.write('\t\t\tcenter: new google.maps.LatLng(%f, %f),\n' %
                (self.center[0], self.center[1]))

        # This is the only line we change
        f.write('\t\t\tmapTypeId: \'{}\'\n'.format(self.map_type))


        f.write('\t\t};\n')
        f.write(
            '\t\tvar map = new google.maps.Map(document.getElementById("map_canvas"), myOptions);\n')
        f.write('\n')

        f.write('\t\tvar bounds = new google.maps.LatLngBounds();\n')
        f.write('\t\tbounds.extend(new google.maps.LatLng(%f, %f));\n' % (self.bounds[0][0], self.bounds[0][1]))
        f.write('\t\tbounds.extend(new google.maps.LatLng(%f, %f));\n' % (self.bounds[1][0], self.bounds[1][1]))

        f.write(
            '\t\tmap.fitBounds(bounds);\n')
        f.write('\n')

def plot_route(route, api_key, override=False, plot_markers=True, map_type='hybrid'):
    route_id = route["route_id"]
    map_filename = f"{MAP_DIR}/{PREFIX}_{route_id}.html"
    if os.path.exists(map_filename) and not override:
        print(f"Map for route {route_id} already exists. Skipping.")
        return map_filename
    # Separate latitudes and longitudes from the lat_lng_path
    latitudes, longitudes = [position["pano_lat"] for position in route["path"]], [position["pano_lng"] for position in route["path"]]
    
    north_bound = max(latitudes)
    south_bound = min(latitudes)
    east_bound = max(longitudes)
    west_bound = min(longitudes)
    # Initialize the map centered on the route's starting location
    gmap = CustomGoogleMapPlotter(
        sum(latitudes)/len(latitudes), sum(longitudes)/len(longitudes), zoom=20, apikey=api_key, 
        map_type = map_type, bounds = [(south_bound, west_bound), (north_bound, east_bound)]
    )
    
    # Plot the route path with scatter points and a line connecting them
    gmap.scatter(latitudes, longitudes, '#FF0000', size=1, marker=False)
    gmap.plot(latitudes, longitudes, 'white', edge_width=10)
    gmap.marker(latitudes[0], longitudes[0], color='#FFC0CB', label='S')
    gmap.marker(latitudes[-1], longitudes[-1], color='#90EE90', label='G')

    # Plot the selected positions with markers
    if plot_markers:
        for i, position in enumerate(route['multiple_choice_positions']):
            gmap.marker(position['lat'], position['lng'], color='cornflowerblue', label=str(i+1))
    
    # Draw the map to an HTML file with a unique name for each route
    gmap.draw(map_filename)
    print(f"Map for route {route_id} saved as {map_filename}")   

    # Update the HTML file to modify the marker icons and markers
    update_html_markers(map_filename, map_filename)

    return map_filename

def html_to_image(html_file, override = False):
    """Converts an HTML file to an image using Selenium and Chrome.

    Args:
        html_file (str): Path to the HTML file.
    """
    screenshot_file = os.path.splitext(html_file)[0] + ".png"
    if not override and os.path.exists(screenshot_file):
        print(f"Screenshot for {html_file} already exists. Skipping.")
        return

    # Set up Chrome WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--kiosk")
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=chrome_options)

    # Load the HTML file
    driver.get(f"file:///{os.path.abspath(html_file)}")

    # Wait for the page to load
    sleep(3)
    # Get the screenshot
    driver.save_screenshot(screenshot_file)
    print("Saved image to ", screenshot_file)

    # Close the browser
    driver.quit()

def load_positions(path):
    with open(path, 'r') as f:
        positions = json.load(f)
    return positions

# Usage
if __name__ == "__main__":
    # Google Maps API key
    data_file = '../data/train_positions_processed_mapped_v2.json'
    api_key = os.getenv("MAPS_API_KEY")
    if api_key is None:
        raise ValueError("API key not found. Please set the MAPS_API_KEY environment variable.")
    else:
        print("API key loaded successfully.")
    
    os.makedirs(MAP_DIR, exist_ok=True)
    # Process routes from JSON file
    routes = load_positions(data_file)
    for route in routes:
        html_file_path = plot_route(route, api_key, override=False, plot_markers=False, map_type='satellite')
        html_to_image(html_file_path, override=False)
    