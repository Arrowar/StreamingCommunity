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
        self.episodes_cache = None

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
    
    def _fetch_all_episodes(self):
        """
        Fetch all episodes data at once and cache it
        """
        try:
            count = self.get_count_episodes()
            if not count:
                return

            response = httpx.get(
                url=f"{self.url}/info_api/{self.media_id}/1",
                params={
                    "start_range": 1,
                    "end_range": count
                },
                headers=self.headers,
                timeout=max_timeout
            )
            response.raise_for_status()
            
            self.episodes_cache = response.json()["episodes"]
        except Exception as e:
            logging.error(f"Error fetching all episodes: {e}")
            self.episodes_cache = None

    def get_info_episode(self, index_ep: int) -> Episode:
        """
        Get episode info from cache
        """
        if self.episodes_cache is None:
            self._fetch_all_episodes()
            
        if self.episodes_cache and 0 <= index_ep < len(self.episodes_cache):
            return Episode(self.episodes_cache[index_ep])
        return None


    # ------------- FOR GUI -------------
    def getNumberSeason(self) -> int:
        """
        Get the total number of seasons available for the anime.
        Note: AnimeUnity typically doesn't have seasons, so returns 1.
        """
        return 1
        
    def selectEpisode(self, season_number: int = 1, episode_index: int = 0) -> Episode:
        """
        Get information for a specific episode.
        """
        return self.get_info_episode(episode_index)
