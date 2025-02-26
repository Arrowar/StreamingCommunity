# 01.03.24

import json
import logging


# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Api.Player.Helper.Vixcloud.util import Season, EpisodeManager


# Variable
max_timeout = config_manager.get_int("REQUESTS", "timeout")


class ScrapeSerie:
    def __init__(self, url):
        """
        Initialize the ScrapeSerie class for scraping TV series information.
        
        Args:
            - url (str): The URL of the streaming site.
        """
        self.is_series = False
        self.headers = {'user-agent': get_userAgent()}
        self.url = url

    def setup(self, media_id: int = None, series_name: str = None):
        """
        Set up the scraper with specific media details.
        
        Args:
            media_id (int, optional): Unique identifier for the media
            series_name (str, optional): Name of the TV series
        """
        self.media_id = media_id

        # If series name is provided, initialize series-specific managers
        if series_name is not None:
            self.is_series = True
            self.series_name = series_name
            self.season_manager = None
            self.episode_manager: EpisodeManager = EpisodeManager()

    def collect_info_title(self) -> None:
        """
        Retrieve season information for a TV series from the streaming site.
        
        Raises:
            Exception: If there's an error fetching season information
        """
        try:
            response = httpx.get(
                url=f"{self.url}/titles/{self.media_id}-{self.series_name}",
                headers=self.headers,
                timeout=max_timeout
            )
            response.raise_for_status()

            # Extract seasons from JSON response
            soup = BeautifulSoup(response.text, "html.parser")
            json_response = json.loads(soup.find("div", {"id": "app"}).get("data-page"))
            self.version = json_response['version']

            # Collect info about season
            self.season_manager = Season(json_response.get("props").get("title"))

        except Exception as e:
            logging.error(f"Error collecting season info: {e}")
            raise

    def collect_info_season(self, number_season: int) -> None:
        """
        Retrieve episode information for a specific season.
        
        Args:
            number_season (int): Season number to fetch episodes for
        
        Raises:
            Exception: If there's an error fetching episode information
        """
        try:
            response = httpx.get(
                url=f'{self.url}/titles/{self.media_id}-{self.series_name}/stagione-{number_season}', 
                headers={
                    'User-Agent': get_userAgent(),
                    'x-inertia': 'true', 
                    'x-inertia-version': self.version,
                },
                timeout=max_timeout
            )
            response.raise_for_status()

            # Extract episodes from JSON response
            json_response = response.json().get('props').get('loadedSeason').get('episodes')
                
            # Add each episode to the episode manager
            for dict_episode in json_response:
                self.episode_manager.add(dict_episode)

        except Exception as e:
            logging.error(f"Error collecting title season info: {e}")
            raise
