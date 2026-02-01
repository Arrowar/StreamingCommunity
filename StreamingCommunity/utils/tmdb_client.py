# 24.08.24

import re
import unicodedata
from difflib import SequenceMatcher


# External libraries
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils import config_manager
from StreamingCommunity.utils.http_client import create_client, get_userAgent


# Variable
console = Console()
api_key = config_manager.login.get("TMDB", "api_key")


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
            response = create_client(headers={"User-Agent": get_userAgent()}).get(url, params=params)
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

    def _slugs_match(self, slug1: str, slug2: str, threshold: float = 0.85) -> bool:
        """Check if two slugs are similar enough using fuzzy matching."""
        ratio = SequenceMatcher(None, slug1, slug2).ratio()
        return ratio >= threshold

    def get_type_and_id_by_slug_year(self, slug: str, year: int, media_type: str = None, language_preference: str = "it"):
        """
        Get the type (movie or tv) and ID from TMDB based on slug and year.
        """
        if media_type == "movie":
            movie_results = self._make_request("search/movie", {"query": slug.replace('-', ' '), "language": language_preference}).get("results", [])
            
            # 1 result
            if len(movie_results) == 1:
                return {'type': "movie", 'id': movie_results[0]['id']}
            
            # Multiple results
            for movie in movie_results:
                title = movie.get('title')
                release_date = movie.get('release_date')
                
                if release_date:
                    movie_year = int(release_date[:4])
                else:
                    continue
                
                movie_slug = self._slugify(title)
                
                # Use fuzzy matching instead of exact comparison
                if self._slugs_match(movie_slug, slug) and movie_year == year:
                    return {'type': "movie", 'id': movie['id']}
            
            return None
            
        elif media_type == "tv":
            tv_results = self._make_request("search/tv", {"query": slug.replace('-', ' '), "language": language_preference}).get("results", [])
            
            # 1 result
            if len(tv_results) == 1:
                return {'type': "tv", 'id': tv_results[0]['id']}
            
            # Multiple results
            for show in tv_results:
                name = show.get('name')
                first_air_date = show.get('first_air_date')
                
                if first_air_date:
                    show_year = int(first_air_date[:4])
                else:
                    continue
                
                show_slug = self._slugify(name)
                
                # Use fuzzy matching instead of exact comparison
                if self._slugs_match(show_slug, slug) and show_year == year:
                    return {'type': "tv", 'id': show['id']}
            
            return None
            
        else:
            print("Media type not specified. Searching both movie and tv.")
            return None

    def get_year_by_slug_and_type(self, slug: str, media_type: str, language_preference: str = "it"):
        """
        Get the year from TMDB based on slug and type (movie or tv).
        Returns the year from the first search result that matches the slug.
        """
        if media_type == "movie":
            results = self._make_request("search/movie", {"query": slug.replace('-', ' '), "language": language_preference}).get("results", [])
            
            # 1 result
            if len(results) == 1:
                return int(results[0]['release_date'][:4])
            
            # Multiple results
            for movie in results:
                title = movie.get('title')
                release_date = movie.get('release_date')
                
                if not release_date:
                    continue
                
                movie_slug = self._slugify(title)
                
                # Use fuzzy matching
                if self._slugs_match(movie_slug, slug):
                    return int(release_date[:4])
                    
        elif media_type == "tv":
            results = self._make_request("search/tv", {"query": slug.replace('-', ' '), "language": language_preference}).get("results", [])
            
            # 1 result
            if len(results) == 1:
                return int(results[0]['first_air_date'][:4])
            
            # Multiple results
            for show in results:
                name = show.get('name')
                first_air_date = show.get('first_air_date')
                
                if not first_air_date:
                    continue
                
                show_slug = self._slugify(name)
                
                # Use fuzzy matching
                if self._slugs_match(show_slug, slug):
                    return int(first_air_date[:4])
        
        return None


tmdb_client = TMDBClient(api_key)