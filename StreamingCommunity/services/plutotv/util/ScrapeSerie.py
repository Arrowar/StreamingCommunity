# 26.11.2025

import logging


# Internal utilities
from StreamingCommunity.utils.http_client import create_client, get_headers
from StreamingCommunity.services._base.object import SeasonManager


# Logic
from .get_license import get_bearer_token


class GetSerieInfo:
    def __init__(self, url):
        """
        Initialize the GetSerieInfo class for scraping TV series information.
        
        Args:
            - url (str): The URL of the streaming site.
        """
        self.url = url + "/seasons"
        self.headers = get_headers()
        self.series_name = None
        self.seasons_manager = SeasonManager()
        self.seasons_data = {}

    def collect_info_title(self) -> None:
        """
        Retrieve general information about the TV series from the streaming site.
        """
        try:
            # Add Bearer token to headers
            bearer_token = get_bearer_token()
            self.headers['authorization'] = f'Bearer {bearer_token}'
            
            response = create_client(headers=self.headers).get(self.url)
            response.raise_for_status()

            # Parse JSON response
            json_response = response.json()
            self.series_name = json_response.get('name', 'Unknown Series')
            seasons_array = json_response.get('seasons', [])
            
            if not seasons_array:
                logging.warning("No seasons found in JSON response")
                return
            
            # Process each season in the array
            for season_obj in seasons_array:
                season_number = season_obj.get('number')
                if season_number is None:
                    logging.warning("Season without number found, skipping")
                    continue
                
                # Store season data indexed by season number
                self.seasons_data[str(season_number)] = season_obj
                
                # Build season structure for SeasonManager
                season_info = {
                    'id': f"season-{season_number}",
                    'number': season_number,
                    'name': f"Season {season_number}",
                    'slug': f"season-{season_number}",
                }
                self.seasons_manager.add_season(season_info)

        except Exception as e:
            logging.error(f"Error collecting series info: {e}")
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
            season = self.seasons_manager.get_season_by_number(number_season)
            if not season:
                logging.error(f"Season {number_season} not found")
                return

            # Get episodes for this season from stored data
            season_key = str(number_season)
            season_data = self.seasons_data.get(season_key, {})
            episodes = season_data.get('episodes', [])
            
            if not episodes:
                logging.warning(f"No episodes found for season {number_season}")
                return
            
            # Sort episodes by episode number in ascending order
            episodes.sort(key=lambda x: x.get('number', 0), reverse=False)
            
            # Transform episodes to match the expected format
            for episode in episodes:
                duration_ms = episode.get('duration', 0)
                duration_minutes = round(duration_ms / 1000 / 60) if duration_ms else 0
                
                episode_data = {
                    'id': episode.get('_id'),
                    'number': episode.get('number'),
                    'name': episode.get('name', f"Episode {episode.get('number')}"),
                    'description': episode.get('description', ''),
                    'duration': duration_minutes,
                    'slug': episode.get('slug', '')
                }
                
                # Add episode to the season's episode manager
                season.episodes.add(episode_data)

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
    
    def get_series_name(self) -> str:
        """
        Get the name of the series.
        """
        if not self.series_name:
            self.collect_info_title()
        return self.series_name