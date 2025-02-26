# 01.03.24

import logging


# External libraries
import httpx


# Internal utilities
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Api.Player.Helper.Vixcloud.util import EpisodeManager, Episode


# Variable
max_timeout = config_manager.get_int("REQUESTS", "timeout")



class ScrapeSerieAnime:
    def __init__(self, url: str):
        """
        Initialize the media scraper for a specific website.
        
        Args:
            url (str): Url of the streaming site
        """
        self.is_series = False
        self.headers = {'user-agent': get_userAgent()}
        self.url = url

    def setup(self, version: str = None, media_id: int = None, series_name: str = None):
        self.version = version
        self.media_id = media_id

        if series_name is not None:
            self.is_series = True
            self.series_name = series_name
            self.obj_episode_manager: EpisodeManager = EpisodeManager()
            
    def get_count_episodes(self):
        """
        Retrieve total number of episodes for the selected media.
        
        Returns:
            int: Total episode count
        """
        try:

            response = httpx.get(
                url=f"{self.url}/info_api/{self.media_id}/", 
                headers=self.headers, 
                timeout=max_timeout
            )
            response.raise_for_status()

            # Parse JSON response and return episode count
            return response.json()["episodes_count"]
        
        except Exception as e:
            logging.error(f"Error fetching episode count: {e}")
            return None
    
    def get_info_episode(self, index_ep: int) -> Episode:
        """
        Fetch detailed information for a specific episode.
        
        Args:
            index_ep (int): Zero-based index of the target episode
        
        Returns:
            Episode: Detailed episode information
        """
        try:

            params = {
                "start_range": index_ep, 
                "end_range": index_ep + 1
            }

            response = httpx.get(
                url=f"{self.url}/info_api/{self.media_id}/{index_ep}", 
                headers=self.headers, 
                params=params, 
                timeout=max_timeout
            )
            response.raise_for_status()

            # Return information about the episode
            json_data = response.json()["episodes"][-1]
            return Episode(json_data)
        
        except Exception as e:
            logging.error(f"Error fetching episode information: {e}")
            return None
