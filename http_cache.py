"""
HTTP Request Caching Module

Provides caching functionality for HTTP requests to reduce API calls and improve performance.
Cache files are stored in the cache/ directory with configurable expiration times.
"""

import os
import pickle
import hashlib
from datetime import datetime, timedelta
import requests


# Cache duration constants (in hours)
CACHE_DURATION_SEASON_OVERVIEW = 24  # Understat season overview
CACHE_DURATION_TEAM_DATA = 24        # Understat team data
CACHE_DURATION_MATCH_DATA = 168      # Understat match data (7 days)
CACHE_DURATION_FPL_API = 1           # FPL API (most dynamic)

# Cache directory
CACHE_DIR = "cache"


def _ensure_cache_dir():
    """Create cache directory if it doesn't exist."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def _get_cache_filename(url):
    """Generate a safe filename from URL using hash."""
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"{url_hash}.pkl")


def _is_cache_valid(cache_data, cache_duration_hours):
    """Check if cached data is still valid based on timestamp."""
    if 'timestamp' not in cache_data:
        return False
    
    cache_time = cache_data['timestamp']
    expiration_time = cache_time + timedelta(hours=cache_duration_hours)
    
    return datetime.now() < expiration_time


def cached_get(url, cache_duration_hours):
    """
    Perform a cached HTTP GET request.
    
    Args:
        url (str): The URL to fetch
        cache_duration_hours (float): How long to cache the response in hours
        
    Returns:
        A response-like object with .text and .json() method
    """
    _ensure_cache_dir()
    
    cache_file = _get_cache_filename(url)
    
    # Check if cache exists and is valid
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            if _is_cache_valid(cache_data, cache_duration_hours):
                print(f"[CACHE HIT] Using cached data for: {url}")
                return CachedResponse(cache_data)
        except Exception as e:
            print(f"[CACHE ERROR] Failed to load cache for {url}: {e}")
    
    # Cache miss or invalid - fetch fresh data
    print(f"[CACHE MISS] Fetching fresh data for: {url}")
    response = requests.get(url)
    
    # Store in cache
    cache_data = {
        'url': url,
        'timestamp': datetime.now(),
        'response_text': response.text,
        'status_code': response.status_code,
        'headers': dict(response.headers)
    }
    
    # Try to parse JSON if applicable
    try:
        cache_data['response_json'] = response.json()
    except:
        cache_data['response_json'] = None
    
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
    except Exception as e:
        print(f"[CACHE WARNING] Failed to save cache for {url}: {e}")
    
    return response


class CachedResponse:
    """
    A response-like object that mimics requests.Response for cached data.
    """
    def __init__(self, cache_data):
        self.text = cache_data['response_text']
        self._json_data = cache_data.get('response_json')
        self.status_code = cache_data.get('status_code', 200)
        self.headers = cache_data.get('headers', {})
        self.url = cache_data['url']
    
    def json(self):
        """Return the JSON-decoded response content."""
        if self._json_data is not None:
            return self._json_data
        raise ValueError("Response content is not JSON")

