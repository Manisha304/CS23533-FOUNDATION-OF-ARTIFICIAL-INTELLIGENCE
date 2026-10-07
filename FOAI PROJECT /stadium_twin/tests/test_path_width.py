import cv2
import numpy as np
import pytest
from unittest.mock import patch
from app.capacity.path_width import measure_path_width, get_metres_per_pixel, TILE_ZOOM

def test_measure_path_width_synthetic():
    img = np.zeros((256, 256, 3), dtype=np.uint8)
    # create a vertical strip 10px wide at x=123 to 133
    img[:, 123:133] = 255
    
    with patch('app.capacity.path_width.fetch_satellite_tile') as mock_fetch:
        # We want lat, lon to result in px=128, py=128
        # x_exact = tx + px / 256 = tx + 0.5
        # y_exact = ty + py / 256 = ty + 0.5
        
        # We can just pass lat=0, lon=0, which gives x_exact=262144.0, y_exact=262144.0
        # If we want px=128, py=128, we need tx=262143.5 which is impossible since tx is int.
        # But wait! We control `tx` and `ty` returned by our mock fetch_satellite_tile.
        # If we return tx=262144, ty=262144, then px=0, py=0.
        # If px=0, py=0, the ROI is taken from img[0:32, 0:32].
        # Let's just put the white strip at x=0 to 10!
        
        lat = 0.0
        lon = 0.0
        
        # We will redefine the image to have a strip near x=0
        img2 = np.zeros((256, 256, 3), dtype=np.uint8)
        img2[:, 0:10] = 255  # 10px wide strip at the left edge
        
        mock_fetch.return_value = (img2, 262144, 262144)
        
        width_m = measure_path_width(lat, lon)
        
        mpp = get_metres_per_pixel(lat, TILE_ZOOM)
        expected_width = 10 * mpp
        
        # 0.5 to 1.5 tolerance because of morphology and distance transform
        assert expected_width * 0.5 <= width_m <= expected_width * 1.5
