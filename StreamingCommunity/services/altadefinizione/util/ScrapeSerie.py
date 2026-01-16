# 16.03.25

import logging


# External libraries
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.utils.http_client import create_client, get_userAgent
from StreamingCommunity.services._base.object import SeasonManager


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
        Retrieve all episodes for all seasons.
        """
        response = create_client(headers=self.headers).get(self.url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Get series name from title
        title_tag = soup.find("title")
        if title_tag:
            self.series_name = title_tag.get_text(strip=True).split(" - ")[0]
        else:
            self.series_name = "Unknown Series"

        # Find the series-select container
        series_select = soup.find('div', class_='series-select')
        if not series_select:
            logging.warning("series-select div not found")
            return

        # Find all season dropdowns
        seasons_dropdown = series_select.find('div', class_='dropdown seasons')
        if not seasons_dropdown:
            logging.warning("seasons dropdown not found")
            return

        season_items = seasons_dropdown.find_all('span', {'data-season': True})
        
        for season_span in season_items:
            try:
                season_num = int(season_span.get('data-season'))
                season_name = season_span.get_text(strip=True)

                # Create a new season
                current_season = self.seasons_manager.add_season({
                    'number': season_num,
                    'name': season_name
                })

                # Find episodes for this season
                episodes_dropdown = series_select.find('div', class_='dropdown episodes', attrs={'data-season': str(season_num)})
                if not episodes_dropdown:
                    continue

                episode_items = episodes_dropdown.find_all('span', {'data-episode': True})
                
                for ep_span in episode_items:
                    try:
                        ep_data = ep_span.get('data-episode')  # format: "season-episode" e.g. "1-1"
                        ep_parts = ep_data.split('-')
                        if len(ep_parts) != 2:
                            continue
                            
                        ep_num = int(ep_parts[1])
                        ep_title = ep_span.get_text(strip=True)

                        # Find the corresponding mirrors div for this episode
                        mirrors_div = series_select.find('div', class_='dropdown mirrors', attrs={'data-season': str(season_num), 'data-episode': ep_data})
                        
                        supervideo_url = None
                        if mirrors_div:
                            
                            # Look for supervideo link (Player 1)
                            mirrors_menu = mirrors_div.find('div', class_='dropdown-menu')
                            if mirrors_menu:
                                # Find the span with data-id="supervideo"
                                supervideo_span = mirrors_menu.find('span', {'data-id': 'supervideo'})
                                if supervideo_span:
                                    supervideo_url = supervideo_span.get('data-link', '').strip()
                        
                        # Only add episode if supervideo link is available
                        if supervideo_url and current_season:
                            current_season.episodes.add({
                                'number': ep_num,
                                'name': ep_title if ep_title else f"Episodio {ep_num}",
                                'url': supervideo_url
                            })
                        else:
                            logging.warning(f"Supervideo link not available for Season {season_num}, Episode {ep_num}")
                            
                    except Exception as e:
                        logging.error(f"Error parsing episode: {e}")
                        continue
                        
            except Exception as e:
                logging.error(f"Error parsing season: {e}")
                continue

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