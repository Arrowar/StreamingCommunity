# 21.05.24

import logging


# External libraries
import httpx


# Internal utilities
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Api.Player.Helper.Vixcloud.util import SeasonManager


# Variable
max_timeout = config_manager.get_int("REQUESTS", "timeout")


class GetSerieInfo:
    def __init__(self, path_id: str):
        """Initialize the GetSerieInfo class."""
        self.base_url = "https://www.raiplay.it"
        self.path_id = path_id
        self.series_name = None
        self.prog_tipology = "film"
        self.prog_description = None
        self.prog_year = None
        self.seasons_manager = SeasonManager()

    def collect_info_title(self) -> None:
        """Get series info including seasons."""
        try:
            program_url = f"{self.base_url}/{self.path_id}"
            response = httpx.get(url=program_url, headers=get_headers(), timeout=max_timeout)
            
            # If 404, content is not yet available
            if response.status_code == 404:
                logging.info(f"Content not yet available: {program_url}")
                return
                
            response.raise_for_status()
            json_data = response.json()

            # Get basic program info
            self.prog_description = json_data.get('program_info', '').get('vanity', '')
            self.prog_year = json_data.get('program_info', '').get('year', '')
            self.series_name = json_data.get('program_info', '').get('title', '')
            
            # Look for seasons in the 'blocks' property
            for block in json_data.get('blocks', []):

                # Check if block is a season block or episodi block
                if block.get('type') == 'RaiPlay Multimedia Block':
                    if block.get('name', '').lower() == 'episodi':
                        self.publishing_block_id = block.get('id')

                        # Extract seasons from sets array
                        for season_set in block.get('sets', []):
                            self.prog_tipology = "tv"

                            if 'stagione' in season_set.get('name', '').lower():
                                self._add_season(season_set, block.get('id'))
                                
                    elif 'stagione' in block.get('name', '').lower():
                        self.publishing_block_id = block.get('id')
                        self.prog_tipology = "tv"

                        # Extract season directly from block's sets
                        for season_set in block.get('sets', []):
                            self._add_season(season_set, block.get('id'))

        except Exception as e:
            logging.error(f"Unexpected error collecting series info: {e}")

    def _add_season(self, season_set: dict, block_id: str):
        self.seasons_manager.add_season({
            'id': season_set.get('id', ''),
            'number': len(self.seasons_manager.seasons) + 1,
            'name': season_set.get('name', ''),
            'path': season_set.get('path_id', ''),
            'episodes_count': season_set.get('episode_size', {}).get('number', 0)
        })

    def collect_info_season(self, number_season: int) -> None:
        """Get episodes for a specific season."""
        try:
            season = self.seasons_manager.get_season_by_number(number_season)

            # Se stai leggendo questo codice spieami perche hai fatto cosi.
            url = f"{self.base_url}/{self.path_id.replace('.json', '')}/{self.publishing_block_id}/{season.id}/episodes.json"
            response = httpx.get(url=url, headers=get_headers(), timeout=max_timeout)
            response.raise_for_status()
            
            episodes_data = response.json()
            cards = []
            
            # Extract episodes from different possible structures 
            if 'seasons' in episodes_data:
                for season_data in episodes_data.get('seasons', []):
                    for episode_set in season_data.get('episodes', []):
                        cards.extend(episode_set.get('cards', []))
            
            if not cards:
                cards = episodes_data.get('cards', [])

            # Add episodes to season
            for ep in cards:
                episode = {
                    'id': ep.get('id', ''),
                    'number': ep.get('episode', ''),
                    'name': ep.get('episode_title', '') or ep.get('toptitle', ''),
                    'duration': ep.get('duration', ''),
                    'url': f"{self.base_url}{ep.get('weblink', '')}" if 'weblink' in ep else f"{self.base_url}{ep.get('url', '')}",
                    'mpd_id': ep.get('video_url').split("=")[1].strip()
                }
                season.episodes.add(episode)

        except Exception as e:
            logging.error(f"Error collecting episodes for season {number_season}: {e}")
            raise


    # ------------- FOR GUI -------------
    def getNumberSeason(self) -> int:
        """
        Get the total number of seasons available for the series.
        """
        if not self.seasons_manager.seasons:
            self.collect_info_title()
            
        return len(self.seasons_manager.seasons)
    
    def getEpisodeSeasons(self, season_number: int) -> list:
        """
        Get all episodes for a specific season.
        """
        season = self.seasons_manager.get_season_by_number(season_number)

        if not season:
            logging.error(f"Season {season_number} not found")
            return []
            
        if not season.episodes.episodes:
            self.collect_info_season(season_number)
            
        return season.episodes.episodes
        
    def selectEpisode(self, season_number: int, episode_index: int) -> dict:
        """
        Get information for a specific episode in a specific season.
        """
        episodes = self.getEpisodeSeasons(season_number)
        if not episodes or episode_index < 0 or episode_index >= len(episodes):
            logging.error(f"Episode index {episode_index} is out of range for season {season_number}")
            return None
            
        return episodes[episode_index]