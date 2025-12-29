# 22.12.25

import logging


# Internal utilities
from StreamingCommunity.Util.http_client import create_client
from StreamingCommunity.Api.Template.object import SeasonManager
from .get_license import get_api


class GetSerieInfo:
    def __init__(self, show_alternate_id, show_id):
        """
        Initialize series scraper for Discovery+
        
        Args:
            show_alternate_id (str): The alternate ID of the show (e.g., 'homestead-rescue-discovery')
            show_id (str): The numeric ID of the show
        """
        self.api = get_api()
        self.show_alternate_id = show_alternate_id
        self.show_id = show_id
        self.series_name = ""
        self.seasons_manager = SeasonManager()
        self.n_seasons = 0
        self.collection_id = None
        self._get_show_info()
       
        
    def _get_show_info(self):
        """Get show information including number of seasons and collection ID"""
        try:
            response = create_client(headers=self.api.get_request_headers()).get(
                f'https://eu1-prod-direct.discoveryplus.com/cms/routes/show/{self.show_alternate_id}',
                params={
                    'include': 'default',
                    'decorators': 'viewingHistory,isFavorite,playbackAllowed'
                },
                cookies=self.api.get_cookies()
            )
            response.raise_for_status()
            data = response.json()
            
            # Get series name from first show element
            for element in data.get('included', []):
                if element.get('type') == 'show':
                    self.series_name = element.get('attributes', {}).get('name', '')
                    break
            
    
            # Get collection ID
            for element in data.get('included', []):
                if element.get('type') == 'collection':
                    self.collection_id = element.get('id')
                    
                    # Get number of seasons
                    if 'filters' in element.get('attributes',{}).get('component',{}):
                        filters = element.get('attributes', {}).get('component', {}).get('filters', [])
                        if filters[0]:
                            self.n_seasons = int(filters[0].get('options',[])[-1].get('value',{}))
            return True
            
        except Exception as e:
            logging.error(f"Failed to get show info: {e}")
            return False
    
    def _get_season_episodes(self, season_number):
        """
        Get episodes for a specific season
        
        Args:
            season_number (int): Season number
        """
        try:
            response = create_client(headers=self.api.get_request_headers()).get(
                f'https://eu1-prod-direct.discoveryplus.com/cms/collections/{self.collection_id}',
                params={
                    'include': 'default',
                    'decorators': 'viewingHistory,isFavorite,playbackAllowed',
                    'pf[seasonNumber]': season_number,
                    'pf[show.id]': self.show_id
                },
                cookies=self.api.get_cookies()
            )
            response.raise_for_status()
            
            data = response.json()
            episodes = []
            
            for element in data.get('included', []):
                if element.get('type') == 'video':
                    attributes = element.get('attributes', {})
                    if 'episodeNumber' in attributes:
                        episodes.append({
                            'id': attributes.get('alternateId', ''),
                            'video_id': element.get('id', ''),
                            'name': attributes.get('name', ''),
                            'episode_number': attributes.get('episodeNumber', 0),
                            'duration': attributes.get('videoDuration', 0) // 60000
                        })
            
            # Sort by episode number
            episodes.sort(key=lambda x: x['episode_number'])
            #print("Add n_episodes:", len(episodes), "for season:", season_number)
            return episodes
            
        except Exception as e:
            logging.error(f"Failed to get episodes for season {season_number}: {e}")
            return []
    
    def collect_season(self):
        """Collect all seasons and episodes"""
        try:
            for season_num in range(1, self.n_seasons + 1):
                episodes = self._get_season_episodes(season_num)
                
                if episodes:
                    season_obj = self.seasons_manager.add_season({
                        'number': season_num,
                        'name': f"Season {season_num}",
                        'id': f"season_{season_num}"
                    })
                    
                    if season_obj:
                        for episode in episodes:
                            season_obj.episodes.add(episode)
        
        except Exception as e:
            logging.error(f"Error in collect_season: {e}")


    # ------------- FOR GUI -------------
    def getNumberSeason(self) -> int:
        """Get total number of seasons"""
        if not self.seasons_manager.seasons:
            self.collect_season()
        return len(self.seasons_manager.seasons)
        
    def getRealNumberSeason(self,index_season:int) -> int:
        """Get the real number of season, not the index"""
        seasons = self.seasons_manager.seasons
        i = 0
        for season in seasons:
            i+=1
            if i == index_season:
                return season.__str__().split("id=season_")[1].split(',')[0]
        return None

    def getEpisodeSeasons(self, season_number: int) -> list:
        """Get all episodes for a specific season"""
        if not self.seasons_manager.seasons:
            self.collect_season()
        
        season_index = season_number - 1
        season = self.seasons_manager.seasons[season_index]
        return season.episodes.episodes
    
    def selectEpisode(self, season_number: int, episode_index: int) -> dict:
        """Get information for a specific episode"""
        episodes = self.getEpisodeSeasons(season_number)
        if not episodes or episode_index < 0 or episode_index >= len(episodes):
            logging.error(f"Episode index {episode_index} out of range for season {season_number}")
            return None
        
        return episodes[episode_index]
