import math
import logging

logger = logging.getLogger(__name__)

def polygon_area_m2(coords_lat_lon: list) -> float:
    """
    Compute the area of a polygon in square metres using the Shoelace formula
    with Haversine-based coordinate conversion.
    coords_lat_lon: list of [lat, lon] pairs
    """
    if len(coords_lat_lon) < 3:
        return 0.0

    # Project to local metres (flat-earth approx, fine for <5 km radius)
    origin_lat = coords_lat_lon[0][0]
    origin_lon = coords_lat_lon[0][1]

    def to_xy(lat, lon):
        x = (lon - origin_lon) * math.radians(1) * 6371000 * math.cos(math.radians(origin_lat))
        y = (lat - origin_lat) * math.radians(1) * 6371000
        return x, y

    pts = [to_xy(c[0], c[1]) for c in coords_lat_lon]

    # Shoelace formula
    n = len(pts)
    area = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def estimate_capacity(polygon_json: list, density: float = 2.5) -> dict:
    """
    Estimate crowd capacity from the stadium polygon.

    Method (classical, explainable):
      1. Compute polygon area in m² using the Shoelace formula.
      2. Assume ~40% of gross area is usable standing/seating space
         (rest is pitch, corridors, concessions).
      3. Apply crowd density:  2.5 people / m²  (normal event, per Green Guide).

    Returns a dict with all intermediate values for viva explainability.
    """
    gross_area_m2 = polygon_area_m2(polygon_json)
    usable_fraction = 0.40
    usable_area_m2 = gross_area_m2 * usable_fraction
    capacity = int(usable_area_m2 * density)

    result = {
        "gross_area_m2": round(gross_area_m2, 1),
        "usable_fraction": usable_fraction,
        "usable_area_m2": round(usable_area_m2, 1),
        "density_per_m2": density,
        "estimated_capacity": capacity,
        "method": (
            "Shoelace formula on OSM polygon → gross area × 0.40 usable fraction "
            f"× {density} people/m² (Green Guide normal density)"
        ),
    }
    logger.info(f"Capacity estimate: {result}")
    return result
