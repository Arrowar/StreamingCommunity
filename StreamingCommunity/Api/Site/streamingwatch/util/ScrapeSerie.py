# 29.04.25

import re
import logging


# External libraries
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.http_client import create_client
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Api.Player.Helper.Vixcloud.util import SeasonManager, Episode


# Variable
max_timeout = config_manager.get_int("REQUESTS", "timeout")


class GetSerieInfo:
    def __init__(self, url):
        self.headers = {'user-agent': get_userAgent()}
        self.url = url
        self.seasons_manager = SeasonManager()
        self.series_name = None
        self.client = create_client(headers=self.headers)

    def collect_info_season(self) -> None:
        """
        Retrieve all series information including episodes and seasons.
        """
        try:
            response = self.client.get(self.url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if not self.series_name:
                title_tag = soup.find('h1', class_='title-border')
                self.series_name = title_tag.get_text(strip=True) if title_tag else 'N/A'
            
            # Extract episodes and organize by season
            episodes = {}
            for ep in soup.find_all('div', class_='bolumust'):
                a_tag = ep.find('a')
                if not a_tag:
                    continue
                
                ep_url = a_tag.get('href', '')
                episode_title = a_tag.get_text(strip=True)
                
                # Clean up episode title by removing season info and date
                clean_title = re.sub(r'Stagione \d+ Episodio \d+\s*\(?([^)]+)\)?\s*\d+\s*\w+\s*\d+', r'\1', episode_title)
                
                season_match = re.search(r'stagione-(\d+)', ep_url)
                if season_match:
                    season_num = int(season_match.group(1))
                    if season_num not in episodes:
                        episodes[season_num] = []
                    
                    episodes[season_num].append({
                        'id': len(episodes[season_num]) + 1,
                        'number': len(episodes[season_num]) + 1,
                        'name': clean_title.strip(),
                        'url': ep_url
                    })
            
            # Add seasons to SeasonManager
            for season_num, eps in episodes.items():
                season = self.seasons_manager.add_season({
                    'id': season_num,
                    'number': season_num,
                    'name': f'Stagione {season_num}'
                })
                
                # Add episodes to season's EpisodeManager
                for ep in eps:
                    season.episodes.add(ep)
                
        except Exception as e:
            logging.error(f"Error collecting series info: {str(e)}")
            raise

    # ------------- FOR GUI -------------
    def getNumberSeason(self) -> int:
        """
        Get the total number of seasons available for the series.
        """
        if not self.seasons_manager.seasons:
            self.collect_info_season()

        return len(self.seasons_manager.seasons)
    
    def getEpisodeSeasons(self, season_number: int) -> list:
        """
        Get all episodes for a specific season.
        """
        if not self.seasons_manager.seasons:
            self.collect_info_season()
            
        season = self.seasons_manager.get_season_by_number(season_number)
        if not season:
            logging.error(f"Season {season_number} not found")
            return []
            
        return season.episodes.episodes
        
    def selectEpisode(self, season_number: int, episode_index: int) -> Episode:
        """
        Get information for a specific episode in a specific season.
        """
        episodes = self.getEpisodeSeasons(season_number)
        if not episodes or episode_index < 0 or episode_index >= len(episodes):
            logging.error(f"Episode index {episode_index} is out of range for season {season_number}")
            return None
            
        return episodes[episode_index]