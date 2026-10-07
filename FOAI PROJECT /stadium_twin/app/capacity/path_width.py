import math
import cv2
import numpy as np
import requests
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# Constants for image analysis
MIN_REALISTIC_WIDTH = 0.3
MAX_REALISTIC_WIDTH = 15.0
CANNY_THRESHOLD1 = 50
CANNY_THRESHOLD2 = 150
TILE_ZOOM = 19
TILE_SIZE = 256

def get_metres_per_pixel(lat: float, zoom: int) -> float:
    return 156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)

def latlon_to_tile(lat: float, lon: float, zoom: int):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y

def fetch_satellite_tile(lat: float, lon: float, zoom: int):
    x, y = latlon_to_tile(lat, lon, zoom)
    url = settings.SATELLITE_TILE_URL.format(z=zoom, x=x, y=y)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return img, x, y
    except Exception as e:
        logger.error(f"Failed to fetch tile: {e}")
    return None, None, None

def measure_path_width(lat: float, lon: float) -> float:
    """
    Estimates the physical width of a path using satellite imagery and classical OpenCV.
    Returns the width in metres, or -1.0 if the measurement is invalid/fails.
    """
    img, tx, ty = fetch_satellite_tile(lat, lon, TILE_ZOOM)
    if img is None:
        return -1.0

    # Calculate exact pixel coordinate within the tile
    n = 2.0 ** TILE_ZOOM
    x_exact = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    y_exact = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    
    px = int((x_exact - tx) * TILE_SIZE)
    py = int((y_exact - ty) * TILE_SIZE)

    # Extract ROI (Region of Interest) around the path coordinate
    roi_size = 64
    x1 = max(0, px - roi_size // 2)
    y1 = max(0, py - roi_size // 2)
    x2 = min(TILE_SIZE, px + roi_size // 2)
    y2 = min(TILE_SIZE, py + roi_size // 2)

    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return -1.0

    # Grayscale & Canny edge detection
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, CANNY_THRESHOLD1, CANNY_THRESHOLD2)

    # Morphological operations to clean edges
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    edges = cv2.erode(edges, kernel, iterations=1)

    # Calculate distance transform from edges to find path width
    # 255 - edges gives 0 on edges and 255 elsewhere
    dist = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 3)
    
    # We sample the distance near the center of the ROI
    # The exact center of ROI corresponds to our lat/lon
    cy = min(roi.shape[0] // 2, dist.shape[0] - 1)
    cx = min(roi.shape[1] // 2, dist.shape[1] - 1)
    
    # Take a small neighborhood around the center to find a median width
    sampled_distances = []
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            sy, sx = cy + dy, cx + dx
            if 0 <= sy < dist.shape[0] and 0 <= sx < dist.shape[1]:
                sampled_distances.append(dist[sy, sx])
                
    if not sampled_distances:
        return -1.0

    median_dist_px = np.median(sampled_distances)
    # The width is roughly 2 * distance to the nearest edge
    width_px = median_dist_px * 2
    
    if width_px <= 0:
        return -1.0
        
    mpp = get_metres_per_pixel(lat, TILE_ZOOM)
    width_m = width_px * mpp

    if MIN_REALISTIC_WIDTH <= width_m <= MAX_REALISTIC_WIDTH:
        return float(width_m)
    
    return -1.0
