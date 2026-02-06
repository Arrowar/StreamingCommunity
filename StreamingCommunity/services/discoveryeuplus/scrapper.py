# 22.12.25

import logging


# Internal utilities
from StreamingCommunity.utils.http_client import create_client_curl
from StreamingCommunity.services._base.object import SeasonManager, Episode, Season


# Logic
from .client import get_client


class GetSerieInfo:
    def __init__(self, show_id: str):
        """
        Initialize series scraper for Discovery+
        
        Args:
            show_id (str): The alternate ID of the show (from search results)
        """
        self.client = get_client()
        self.show_id = show_id
        self.series_name = ""
        self.seasons_manager = SeasonManager()
        self.n_seasons = 0
        self._all_episodes = None
        self._get_show_info()
        
    def _fetch_all_episodes(self):
        """Fetch all episodes for the show (logic moved from get_license.py)"""
        try:
            url = f"{self.client.base_url}/cms/routes/show/{self.show_id}"
            params = {
                'include': 'default',
                'decorators': 'viewingHistory,badges,isFavorite,contentAction',
            }
            
            response = create_client_curl(headers=self.client.headers, cookies=self.client.cookies).get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Find show info
            show_info = next((x for x in data['included'] if x.get('attributes', {}).get('alternateId', '') == self.show_id), None)
            if not show_info:
                logging.error(f"Show info not found for: {self.show_id}")
                return []
                
            show_name = show_info['attributes'].get('name', 'Unknown')
            self.series_name = show_name
            
            # Find episodes content
            content = next((x for x in data['included'] if 'show-page-rail-episodes-tabbed-content' in x['attributes'].get('alias', '')), None)
            
            if not content:
                logging.error(f"No episodes found for show {self.show_id}")
                return []
            
            content_id = content.get('id')
            show_params = content['attributes']['component'].get('mandatoryParams', '')
            season_params = [x.get('parameter') for x in content['attributes']['component']['filters'][0]['options']]
            
            all_episodes = []
            
            # Get episodes for each season
            for season_param in season_params:
                coll_url = f"{self.client.base_url}/cms/collections/{content_id}?{season_param}&{show_params}"
                coll_params = {
                    'include': 'default',
                    'decorators': 'viewingHistory,badges,isFavorite,contentAction',
                }
                
                response = create_client_curl(headers=self.client.headers, cookies=self.client.cookies).get(coll_url, params=coll_params)
                response.raise_for_status()
                
                season_data = response.json()
                
                for item in season_data.get('included', []):
                    if item.get('type') == 'video' and item.get('attributes', {}).get('videoType') == 'EPISODE':
                        attrs = item['attributes']
                        edit_id = item['relationships']['edit']['data']['id']
                        
                        episode = {
                            'id': edit_id,
                            'show': show_name,
                            'season': attrs.get('seasonNumber'),
                            'episode': attrs.get('episodeNumber'),
                            'title': attrs.get('name'),
                        }
                        all_episodes.append(episode)
            
            all_episodes.sort(key=lambda x: (x['season'], x['episode']))
            return all_episodes
            
        except Exception as e:
            logging.error(f"Error in _fetch_all_episodes: {e}")
            return []

    def _get_show_info(self):
        """Get show information and cache episodes list"""
        try:
            if self._all_episodes is None:
                self._all_episodes = self._fetch_all_episodes()
            
            if not self._all_episodes:
                return False
            
            # Get number of seasons from actual distinct season numbers
            seasons_set = set(ep['season'] for ep in self._all_episodes)
            self.n_seasons = len(seasons_set)
            self.seasons_list = sorted(list(seasons_set))
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to get show info: {e}")
            return False
    
    def _get_season_episodes(self, season_number: int):
        """
        Get episodes for a specific season from cache
        
        Args:
            season_number (int): Season number
            
        Returns:
            list: List of episodes for the season
        """
        try:
            if self._all_episodes is None:
                self._all_episodes = self._fetch_all_episodes()
            
            if not self._all_episodes:
                return []
            
            # Filter episodes for the specific season
            season_episodes = []
            for episode in self._all_episodes:
                if episode['season'] == season_number:
                    season_episodes.append({
                        'id': episode['id'],
                        'video_id': episode['id'],
                        'name': episode['title'],
                        'episode_number': episode['episode'],
                        'duration': 0
                    })
            
            # Sort by episode number
            season_episodes.sort(key=lambda x: x['episode_number'])
            logging.info(f"Using cached n_episodes: {len(season_episodes)} for season: {season_number}")
            return season_episodes
            
        except Exception as e:
            logging.error(f"Failed to get episodes for season {season_number}: {e}")
            return []
    
    def collect_season(self):
        """Collect all seasons and episodes"""
        try:
            # Iterate over actual season numbers instead of range(1, n+1)
            for season_num in self.seasons_list:
                episodes = self._get_season_episodes(season_num)
                
                if episodes:
                    season_obj = self.seasons_manager.add(Season(
                        number=season_num,
                        name=f"Season {season_num}",
                        id=f"season_{season_num}"
                    ))
                    
                    if season_obj:
                        for ep in episodes:
                            season_obj.episodes.add(Episode(
                                id=ep.get('id'),
                                video_id=ep.get('video_id'),
                                name=ep.get('name'),
                                number=ep.get('episode_number'),
                                duration=ep.get('duration')
                            ))
                            
        except Exception as e:
            logging.error(f"Error in collect_season: {e}")

    
    # ------------- FOR GUI -------------
    def getNumberSeason(self) -> int:
        """Get total number of seasons"""
        if not self.seasons_manager.seasons:
            self.collect_season()
        return len(self.seasons_manager.seasons)
    
    def getEpisodeSeasons(self, season_number: int) -> list:
        """Get all episodes for a specific season"""
        if not self.seasons_manager.seasons:
            self.collect_season()
        
        season = self.seasons_manager.get_season_by_number(season_number)
        if season:
            return season.episodes.episodes
        
        return []
    
    def selectEpisode(self, season_number: int, episode_index: int) -> Episode:
        """Get information for a specific episode"""
        episodes = self.getEpisodeSeasons(season_number)
        if not episodes or episode_index < 0 or episode_index >= len(episodes):
            logging.error(f"Episode index {episode_index} out of range for season {season_number}")
            return None
        
        return episodes[episode_index]