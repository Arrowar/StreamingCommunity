# 24.08.24

import re
import unicodedata


# External libraries
import httpx
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils import config_manager


# Variable
console = Console()
api_key = config_manager.login.get("TMDB", "api_key")
MAX_TIMEOUT = config_manager.config.get_int("REQUESTS", "timeout")


class TMDBClient:
    def __init__(self, api_key):
        """
        Initialize the class with the API key.
        
        Parameters:
            - api_key (str): The API key for authenticating requests to TheMovieDB.
        """
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"

    def _make_request(self, endpoint, params=None):
        """
        Make a request to the given API endpoint with optional parameters.
        
        Parameters:
            - endpoint (str): The API endpoint to hit.
            - params (dict): Additional parameters for the request.
        
        Returns:
            dict: JSON response as a dictionary.
        """
        try:
            if params is None:
                params = {}

            params['api_key'] = self.api_key
            url = f"{self.base_url}/{endpoint}"
            response = httpx.get(url, params=params, timeout=MAX_TIMEOUT)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            console.log(f"[red]Error making request to {endpoint}: {e}[/red]")
            return {}

    def _slugify(self, text):
        """Normalize and slugify a given text."""
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        text = re.sub(r'[^\w\s-]', '', text).strip().lower()
        text = re.sub(r'[-\s]+', '-', text)
        return text

    def get_type_and_id_by_slug_year(self, slug: str, year: int):
        """
        Get the type (movie or tv) and ID from TMDB based on slug and year.
        """
        movie_results = self._make_request("search/movie", {"query": slug.replace('-', ' ')}).get("results", [])
        for movie in movie_results:
            title = movie.get('title', '')
            release_date = movie.get('release_date', '')

            if release_date:
                movie_year = int(release_date[:4])
            else:
                continue

            movie_slug = self._slugify(title)
            if movie_slug == slug and movie_year == year:
                return {'type': "movie", 'id': movie['id']}

        tv_results = self._make_request("search/tv", {"query": slug.replace('-', ' ')}).get("results", [])
        for show in tv_results:
            name = show.get('name', '')
            first_air_date = show.get('first_air_date', '')
            
            if first_air_date:
                show_year = int(first_air_date[:4])
            else:
                continue

            show_slug = self._slugify(name)
            if show_slug == slug and show_year == year:
                return {'type': "tv", 'id': show['id']}

        return None


tmdb_client = TMDBClient(api_key)