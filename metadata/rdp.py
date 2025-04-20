# unmodified from GPT code yet
"""
The Ramer-Douglas-Peucker (RDP) algorithm simplifies a polyline by removing points that do not significantly change its overall shape. The remaining points will be the ones where the path “turns” in a global sense.

Steps
    Convert Your Path: Your path is a list of latitude–longitude pairs. Although RDP works with any 2D coordinates, if your path spans a large geographic area you might want to convert from lat/lon to a metric coordinate system (e.g. UTM). For small areas (or when you’re not super concerned with exact distances), you can process the lat/lon directly.
    Run RDP: Apply the RDP algorithm with a chosen tolerance (e.g. in degrees, meters, or an appropriate unit based on your conversion). A higher tolerance removes more points (keeping only the big “turns”).
    Extract Indices: When running RDP, record the indices of the points kept. These indices correspond to where the significant changes occur in your original path.
    Optional - Compute Turn Angles: For each “corner” identified in the simplified path (except the first and last), compute the change in heading between the incoming segment and the outgoing segment. This will give you the magnitude of the turn.

Python Example Using RDP below. You can implement RDP (or use an existing implementation like rdp on github):

Note:
Another method is to compute the heading (bearing) at each step along the path, smooth the heading signal to filter out noise, and then detect significant changes (peaks in the derivative of the heading).

Steps
    Compute Headings: For each consecutive pair of coordinates, compute the heading.
    Smooth the Heading Signal: Use a moving average or another filter (e.g., a Gaussian filter) to smooth out slight variations.
    Compute the Derivative (Angular Change): Calculate the difference between successive smoothed headings to get a “turn rate” at each step.
    Peak Detection: Apply a peak detection algorithm (for example, using SciPy’s find_peaks) to detect where significant turn changes occur.
    Map Peaks to Indices: Use the indices from the peak detection to mark the approximate turning positions along your original path.

Considerations
    Thresholds: You’ll need to set thresholds for what constitutes a “big turn” versus small fluctuations. Adjust the smoothing window size and peak detection parameters accordingly.
    Handling Angle Wraparound: When dealing with angles, remember that they wrap around (e.g. from 359° back to 0°). Ensure you adjust your differences accordingly (e.g. by working in a circular space).
"""
import math
from typing import List, Tuple

def rdp(points: List[Tuple[float, float]], epsilon: float) -> Tuple[List[Tuple[float, float]], List[int]]:
    """
    A simple recursive implementation of the Ramer-Douglas-Peucker algorithm.
    Returns a tuple (simplified_points, indices) where 'indices' are the positions in the
    original list corresponding to the simplified_points.
    """
    if len(points) < 3:
        return points, list(range(len(points)))
    
    # Line from start to end
    start, end = points[0], points[-1]
    max_dist = 0
    index = 0
    for i in range(1, len(points)-1):
        # Compute perpendicular distance from point to the line (start, end).
        dist = perpendicular_distance(points[i], start, end)
        if dist > max_dist:
            index = i
            max_dist = dist

    if max_dist > epsilon:
        # Recursively simplify
        first_half, indices_first = rdp(points[:index+1], epsilon)
        second_half, indices_second = rdp(points[index:], epsilon)
        # Remove duplicate at the junction
        return (first_half[:-1] + second_half, indices_first[:-1] + [i + index for i in indices_second])
    else:
        return [start, end], [0, len(points)-1]

def perpendicular_distance(point: Tuple[float, float], start: Tuple[float, float], end: Tuple[float, float]) -> float:
    """Compute the perpendicular distance from point to the line defined by start and end."""
    # If start and end are the same, return the Euclidean distance.
    if start == end:
        return math.hypot(point[0]-start[0], point[1]-start[1])
    
    num = abs((end[1]-start[1])*point[0] - (end[0]-start[0])*point[1] + end[0]*start[1] - end[1]*start[0])
    den = math.hypot(end[1]-start[1], end[0]-start[0])
    return num / den

def compute_heading(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Compute the bearing (in degrees) from p1 to p2."""
    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.atan2(x, y)
    bearing_deg = (math.degrees(bearing) + 360) % 360
    return bearing_deg

# Example usage:
if __name__ == "__main__":
    # Replace with your actual lat/lon list.
    path = [
        (40.733685, -74.00278),
        (40.733609, -74.00282),
        (40.733587, -74.002799),
        (40.733501, -74.002713),
        (40.733453, -74.002665),
        (40.733348, -74.002634),
        (40.733365, -74.002579),
    ]
    
    # Set a tolerance; this will depend on the scale of your coordinates.
    tolerance = 0.00005  # Adjust accordingly
    simplified_path, indices = rdp(path, tolerance)
    print("Simplified Path:", simplified_path)
    print("Indices in original path:", indices)
    
    # Optionally, compute turn angles at the simplified vertices
    turns = []
    for i in range(1, len(simplified_path)-1):
        heading_before = compute_heading(simplified_path[i-1], simplified_path[i])
        heading_after = compute_heading(simplified_path[i], simplified_path[i+1])
        turn_angle = (heading_after - heading_before + 360) % 360
        # Adjust for turns > 180 degrees.
        if turn_angle > 180:
            turn_angle = 360 - turn_angle
        turns.append({"index": indices[i], "turn_angle": turn_angle})
    print("Detected Turns:", turns)
