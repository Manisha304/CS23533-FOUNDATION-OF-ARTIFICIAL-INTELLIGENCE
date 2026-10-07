import requests
import time
import logging

logger = logging.getLogger(__name__)

# Nominatim requires a descriptive User-Agent and max 1 req/sec
HEADERS = {
    "User-Agent": "StadiumTwin_v2_Academic_Project/1.0 (educational use, college project)",
    "Accept-Language": "en",
}
LAST_CALL = 0.0

def search_location(query: str):
    """Search for a place using Nominatim. Returns list of results."""
    global LAST_CALL

    # Rate limit: 1 request per second
    now = time.time()
    wait = 1.0 - (now - LAST_CALL)
    if wait > 0:
        time.sleep(wait)
    LAST_CALL = time.time()

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 8,
        "addressdetails": 1,
    }

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        logger.info(f"Nominatim search '{query}': status {response.status_code}")
        if response.status_code != 200:
            logger.error(f"Nominatim returned {response.status_code}: {response.text[:200]}")
            return []
        results = response.json()
        logger.info(f"Nominatim returned {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Nominatim search failed: {e}")
        return []
