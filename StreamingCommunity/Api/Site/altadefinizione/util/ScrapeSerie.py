# 16.03.25

import logging


# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Api.Player.Helper.Vixcloud.util import SeasonManager


# Variable
max_timeout = config_manager.get_int("REQUESTS", "timeout")


class GetSerieInfo:
    def __init__(self, url):
        """
        Initialize the GetSerieInfo class for scraping TV series information.
        
        Args:
            - url (str): The URL of the streaming site.
        """
        self.headers = {'user-agent': get_userAgent()}
        self.url = url
        self.seasons_manager = SeasonManager()

    def collect_season(self) -> None:
        """
        Retrieve all episodes for all seasons
        """
        response = httpx.get(self.url, headers=self.headers)
        soup = BeautifulSoup(response.text, "html.parser")
        self.series_name = soup.find("title").get_text(strip=True).split(" - ")[0]

        # Find all season dropdowns
        seasons_dropdown = soup.find('div', class_='dropdown seasons')
        if not seasons_dropdown:
            return

        # Get all season items
        season_items = seasons_dropdown.find_all('span', {'data-season': True})
        
        for season_item in season_items:
            season_num = int(season_item['data-season'])
            season_name = season_item.get_text(strip=True)
            
            # Create a new season
            current_season = self.seasons_manager.add_season({
                'number': season_num,
                'name': season_name
            })
            
            # Find all episodes for this season
            episodes_container = soup.find('div', {'class': 'dropdown mirrors', 'data-season': str(season_num)})
            if not episodes_container:
                continue
                
            # Get all episode mirrors for this season
            episode_mirrors = soup.find_all('div', {'class': 'dropdown mirrors', 
                                                   'data-season': str(season_num)})
            
            for mirror in episode_mirrors:
                episode_data = mirror.get('data-episode', '').split('-')
                if len(episode_data) != 2:
                    continue
                    
                ep_num = int(episode_data[1])
                
                # Find supervideo link
                supervideo_span = mirror.find('span', {'data-id': 'supervideo'})
                if not supervideo_span:
                    continue
                    
                episode_url = supervideo_span.get('data-link', '')
                
                # Add episode to the season
                if current_season:
                    current_season.episodes.add({
                        'number': ep_num,
                        'name': f"Episodio {ep_num}",
                        'url': episode_url
                    })


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
            
        # Get season directly by its number
        season = self.seasons_manager.get_season_by_number(season_number)
        return season.episodes.episodes if season else []
        
    def selectEpisode(self, season_number: int, episode_index: int) -> dict:
        """
        Get information for a specific episode in a specific season.
        """
        episodes = self.getEpisodeSeasons(season_number)
        if not episodes or episode_index < 0 or episode_index >= len(episodes):
            logging.error(f"Episode index {episode_index} is out of range for season {season_number}")
            return None
            
        return episodes[episode_index]