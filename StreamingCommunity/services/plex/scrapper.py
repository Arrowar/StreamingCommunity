# 12.02.26

import logging
from typing import List, Optional, Dict, Any


# Internal utilities
from StreamingCommunity.services._base.object import SeasonManager, Episode, Season
from .client import get_client


# Variable
BASE_URL = "https://vod.provider.plex.tv"
SCREEN_ENDPOINT = "https://luma.plex.tv/api/screen"
PROVIDER = "provider://tv.plex.provider.vod"


class GetSerieInfo:
    @staticmethod
    def get_movie_info(slug: str) -> Optional[Dict[str, Any]]:
        """Get movie information"""
        api = get_client()
        try:
            r = api.client.get(f"{BASE_URL}/library/metadata/movie:{slug}")
            r.raise_for_status()
            data = r.json()
            movie = data.get("MediaContainer", {}).get("Metadata", [])[0]
            return movie
        except Exception as e:
            logging.error(f"Error fetching movie info for {slug}: {e}")
            return None

    @staticmethod
    def get_series_info(slug: str) -> Optional[Dict[str, Any]]:
        """Get series seasons"""
        api = get_client()
        try:
            r = api.client.get(f"{BASE_URL}/library/metadata/show:{slug}")
            r.raise_for_status()
            data = r.json()
            meta_key = data.get("MediaContainer", {}).get("Metadata", [])[0].get("key")
            
            if not meta_key:
                return None
            
            r = api.client.get(f"{BASE_URL}{meta_key}")
            r.raise_for_status()
            series_data = r.json()
            
            return series_data.get("MediaContainer", {})
        except Exception as e:
            logging.error(f"Error fetching series info for {slug}: {e}")
            return None

    @staticmethod
    def get_season_episodes(season_key: str) -> List[Dict[str, Any]]:
        """Get episodes from a season"""
        api = get_client()
        try:
            r = api.client.get(f"{BASE_URL}{season_key}")
            r.raise_for_status()
            data = r.json()
            return data.get("MediaContainer", {}).get("Metadata", [])
        except Exception as e:
            logging.error(f"Error fetching season episodes for {season_key}: {e}")
            return []

    def __init__(self, url: str):
        self.url = url
        self.slug = url.split('/')[-1] if 'watch.plex.tv' in url else url
        self.seasons_manager = SeasonManager()
        self.series_name = ""
        self.series_data = None

    def collect_season(self) -> None:
        """
        Retrieve all seasons and episodes from Plex API.
        """
        try:
            self.series_data = self.get_series_info(self.slug)
            if not self.series_data:
                return

            metadata = self.series_data.get("Metadata", [])
            if not metadata:
                return

            self.series_name = metadata[0].get("parentTitle") or metadata[0].get("title", "")
            
            for season_meta in metadata:
                season_num = season_meta.get("index")
                if season_num is None:
                    continue
                
                season_obj = self.seasons_manager.add(Season(
                    number=season_num,
                    name=season_meta.get("title", f"Stagione {season_num}"),
                    id=season_meta.get("ratingKey"),
                    url=season_meta.get("key")
                ))
                
                # Fetch episodes for this season
                episodes_data = self.get_season_episodes(season_meta.get("key"))
                for ep_meta in episodes_data:
                    episode = Episode(
                        id=ep_meta.get("ratingKey"),
                        number=ep_meta.get("index"),
                        name=ep_meta.get("title"),
                        url=ep_meta.get("key"),
                        media=ep_meta.get("Media", []) # Store media info directly
                    )
                    season_obj.episodes.add(episode)
        
        except Exception as e:
            logging.error(f"Error in Plex collect_season: {str(e)}")

    
    # ------------- FOR GUI -------------
    def getNumberSeason(self) -> int:
        """
        Get the total number of seasons available for the series.
        """
        if not self.seasons_manager.seasons:
            self.collect_season()
            
        return len(self.seasons_manager.seasons)
    
    def getEpisodeSeasons(self, season_number: int) -> list:
        """
        Get all episodes for a specific season.
        """
        if not self.seasons_manager.seasons:
            self.collect_season()

        season = self.seasons_manager.get_season_by_number(season_number)
        if season:
            return season.episodes.episodes

        return []
        
    def selectEpisode(self, season_number: int, episode_index: int) -> Episode:
        """
        Get information for a specific episode in a specific season.
        """
        episodes = self.getEpisodeSeasons(season_number)
        if not episodes or episode_index < 0 or episode_index >= len(episodes):
            return None
            
        return episodes[episode_index]