# 13.06.24

import logging
from typing import List, Dict


# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.config_json import config_manager


# Logic class
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Variable
max_timeout = config_manager.get_int("REQUESTS", "timeout")


class GetSerieInfo:
    def __init__(self, dict_serie: MediaItem) -> None:
        """
        Initializes the GetSerieInfo object with default values.

        Parameters:
            dict_serie (MediaItem): Dictionary containing series information (optional).
        """
        self.headers = {'user-agent': get_userAgent()}
        self.url = dict_serie.url
        self.tv_name = None
        self.list_episodes = None

    def get_seasons_number(self) -> int:
        """
        Retrieves the number of seasons of a TV series.

        Returns:
            int: Number of seasons of the TV series. Returns -1 if parsing fails.
        """
        try:
            # Make an HTTP request to the series URL
            response = httpx.get(self.url, headers=self.headers, timeout=max_timeout, follow_redirects=True)
            response.raise_for_status()

            # Find the seasons container
            soup = BeautifulSoup(response.text, "html.parser")
            table_content = soup.find('div', class_="tt_season")
            seasons_number = len(table_content.find_all("li"))
            
            # Try to get the title, with fallback
            self.tv_name = soup.find('h1', class_="front_title").get_text(strip=True) if soup.find('h1', class_="front_title") else "Unknown Series"

            return seasons_number

        except Exception as e:
            logging.error(f"Error parsing HTML page: {str(e)}")
            return -1

    def get_episode_number(self, n_season: int) -> List[Dict[str, str]]:
        """
        Retrieves the number of episodes for a specific season.

        Parameters:
            n_season (int): The season number.

        Returns:
            List[Dict[str, str]]: List of dictionaries containing episode information.
        """
        try:

            # Make an HTTP request to the series URL
            response = httpx.get(self.url, headers=self.headers, timeout=max_timeout, follow_redirects=True)
            response.raise_for_status()

            # Parse HTML content of the page
            soup = BeautifulSoup(response.text, "html.parser")

            # Find the container of episodes for the specified season
            table_content = soup.find('div', class_="tab-pane", id=f"season-{n_season}")
            episode_content = table_content.find_all("li")
            list_dict_episode = []

            for episode_div in episode_content:
                index = episode_div.find("a").get("data-num")
                link = episode_div.find("a").get("data-link")
                name = episode_div.find("a").get("data-num")

                obj_episode = {
                    'number': index,
                    'name': name,
                    'url': link
                }
                
                list_dict_episode.append(obj_episode)

            self.list_episodes = list_dict_episode
            return list_dict_episode
        
        except Exception as e:
            logging.error(f"Error parsing HTML page: {e}")

        return []


    # ------------- FOR GUI -------------
    def getNumberSeason(self) -> int:
        """
        Get the total number of seasons available for the series.
        """
        return self.get_seasons_number()
    
    def getEpisodeSeasons(self, season_number: int) -> list:
        """
        Get all episodes for a specific season.
        """
        episodes = self.get_episode_number(season_number)
        return episodes
        
    def selectEpisode(self, season_number: int, episode_index: int) -> dict:
        """
        Get information for a specific episode in a specific season.
        """
        episodes = self.getEpisodeSeasons(season_number)
        if not episodes or episode_index < 0 or episode_index >= len(episodes):
            logging.error(f"Episode index {episode_index} is out of range for season {season_number}")
            return None
            
        return episodes[episode_index]