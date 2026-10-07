import requests
import logging
import math

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "StadiumTwin_v2_Academic_Project/1.0 (educational use)",
    "Accept": "*/*",
}

def fetch_osm_around(lat: float, lon: float, radius_m: int = 500):
    """
    Fetches OSM elements around a point.
    Strategy:
      1. Use Nominatim to find the main polygon (stadium/park boundary).
      2. Use OSM API map endpoint to get nearby roads, paths, and gates.
    Falls back to Overpass if available.
    """
    elements = []
    
    # --- Step 1: Get the main polygon via Nominatim reverse + search ---
    polygon_coords = _fetch_polygon_nominatim(lat, lon)
    
    # --- Step 2: Get nearby ways and nodes via OSM map API ---
    map_elements = _fetch_map_bbox(lat, lon, radius_m)
    elements.extend(map_elements)
    
    # --- Step 3: Try Overpass as bonus (may fail, that's OK) ---
    overpass_elements = _try_overpass(lat, lon, radius_m)
    if overpass_elements:
        # Merge: use Overpass data which is richer
        elements = overpass_elements
    
    # Inject polygon as a synthetic way if we got it from Nominatim
    if polygon_coords and not _has_leisure_way(elements):
        synthetic_nodes = []
        for i, (plon, plat) in enumerate(polygon_coords):
            node_id = 9000000000 + i
            elements.append({"type": "node", "id": node_id, "lat": plat, "lon": plon})
            synthetic_nodes.append(node_id)
        elements.append({
            "type": "way",
            "id": 9000000000,
            "nodes": synthetic_nodes,
            "tags": {"leisure": "stadium", "name": "Main Boundary"}
        })
    
    logger.info(f"Total OSM elements collected: {len(elements)}")
    return {"elements": elements}


def _fetch_polygon_nominatim(lat, lon):
    """Use Nominatim search to get a polygon around the point."""
    try:
        # First try reverse geocode to find what's at this location
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "polygon_geojson": 1, "zoom": 17},
            headers=HEADERS,
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            geojson = data.get("geojson", {})
            if geojson.get("type") == "Polygon" and geojson.get("coordinates"):
                coords = geojson["coordinates"][0]
                logger.info(f"Nominatim polygon found: {len(coords)} points")
                return coords
        
        # Fallback: search for nearby stadium/leisure
        r2 = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": f"stadium near {lat},{lon}",
                "format": "json",
                "polygon_geojson": 1,
                "limit": 1,
                "viewbox": f"{lon-0.01},{lat+0.01},{lon+0.01},{lat-0.01}",
                "bounded": 1,
            },
            headers=HEADERS,
            timeout=15,
        )
        if r2.status_code == 200:
            results = r2.json()
            if results:
                geojson = results[0].get("geojson", {})
                if geojson.get("type") == "Polygon" and geojson.get("coordinates"):
                    coords = geojson["coordinates"][0]
                    logger.info(f"Nominatim search polygon found: {len(coords)} points")
                    return coords
    except Exception as e:
        logger.warning(f"Nominatim polygon fetch failed: {e}")
    return None


def _fetch_map_bbox(lat, lon, radius_m):
    """Use the OSM API /api/0.6/map endpoint to get all data in a bounding box."""
    try:
        # Convert radius to degree offset (rough approximation)
        dlat = radius_m / 111320.0
        dlon = radius_m / (111320.0 * math.cos(math.radians(lat)))
        
        bbox = f"{lon - dlon},{lat - dlat},{lon + dlon},{lat + dlat}"
        
        r = requests.get(
            f"https://api.openstreetmap.org/api/0.6/map.json?bbox={bbox}",
            headers=HEADERS,
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            elements = data.get("elements", [])
            logger.info(f"OSM map API returned {len(elements)} elements")
            return elements
        else:
            logger.warning(f"OSM map API returned {r.status_code}")
    except Exception as e:
        logger.warning(f"OSM map API failed: {e}")
    return []


def _try_overpass(lat, lon, radius_m):
    """Try Overpass API as a bonus data source. Returns [] if it fails."""
    query = f"""
    [out:json][timeout:25];
    (
      way["leisure"](around:{radius_m},{lat},{lon});
      way["building"="stadium"](around:{radius_m},{lat},{lon});
      way["highway"~"footway|pedestrian|path|steps|residential|service"](around:{radius_m},{lat},{lon});
      node["entrance"](around:{radius_m},{lat},{lon});
      node["barrier"~"gate|turnstile"](around:{radius_m},{lat},{lon});
    );
    out body;
    >;
    out skel qt;
    """
    
    urls = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
    ]
    
    for url in urls:
        try:
            r = requests.post(url, data={"data": query}, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                elems = data.get("elements", [])
                if elems:
                    logger.info(f"Overpass success: {len(elems)} elements from {url}")
                    return elems
        except Exception:
            pass
    return []


def _has_leisure_way(elements):
    for el in elements:
        if el.get("type") == "way":
            tags = el.get("tags", {})
            if "leisure" in tags or tags.get("building") == "stadium":
                return True
    return False

def fetch_emergency_services(lat: float, lon: float, radius_m: int = 5000) -> list:
    """Fetch nearby hospitals, police stations, and fire stations using Overpass."""
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"hospital|clinic|police|fire_station"](around:{radius_m},{lat},{lon});
      way["amenity"~"hospital|clinic|police|fire_station"](around:{radius_m},{lat},{lon});
    );
    out center;
    """
    
    urls = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
    ]
    
    for url in urls:
        try:
            r = requests.post(url, data={"data": query}, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                elems = data.get("elements", [])
                logger.info(f"Overpass fetched {len(elems)} emergency services from {url}")
                return elems
        except Exception as e:
            logger.warning(f"Failed to fetch emergency services from {url}: {e}")
    return []
