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

        # Find the tabs holder
        tabs_holder = soup.find('div', id='tabs_holder')
        if not tabs_holder:
            logging.warning("tabs_holder div not found")
            return

        # Find the season tabs
        tt_season = tabs_holder.find('div', class_='tt_season')
        if not tt_season:
            logging.warning("tt_season div not found")
            return

        season_links = tt_season.find_all('a', {'data-toggle': 'tab'})
        
        for season_link in season_links:
            try:
                # Extract season number from href (e.g., "#season-1" -> 1)
                href = season_link.get('href', '')
                if not href.startswith('#season-'):
                    continue
                    
                season_num = int(href.replace('#season-', ''))
                season_name = f"Stagione {season_num}"

                # Create a new season
                current_season = self.seasons_manager.add_season({
                    'number': season_num,
                    'name': season_name
                })

                # Find the corresponding tab pane
                tab_pane = tabs_holder.find('div', id=f'season-{season_num}')
                if not tab_pane:
                    logging.warning(f"Tab pane for season {season_num} not found")
                    continue

                # Find all episode items in this season
                episode_items = tab_pane.find_all('li')
                
                for ep_item in episode_items:
                    try:
                        # Find the main episode link
                        ep_link = ep_item.find('a', {'data-link': True})
                        if not ep_link:
                            continue
                        
                        # Extract episode data
                        data_num = ep_link.get('data-num', '')  # format: "1x1", "1x2", etc.
                        data_title = ep_link.get('data-title', '')
                        supervideo_url = ep_link.get('data-link', '').strip()
                        
                        if not data_num:
                            continue
                        
                        # Parse episode number from data-num (e.g., "1x1" -> episode 1)
                        parts = data_num.split('x')
                        if len(parts) != 2:
                            continue
                            
                        ep_num = int(parts[1])
                        
                        # Extract episode title from data-title
                        ep_title = f"Episodio {ep_num}"
                        if data_title:
                            # Remove "Episodio X: " prefix if present
                            if data_title.startswith(f"Episodio {ep_num}:"):
                                ep_title = data_title[len(f"Episodio {ep_num}: "):].strip()
                            elif data_title.startswith(f"Episodio {ep_num}"):
                                ep_title = data_title
                            else:
                                ep_title = data_title
                        
                        # Alternative: check mirrors div for supervideo link
                        if not supervideo_url or supervideo_url == '#':
                            mirrors_div = ep_item.find('div', class_='mirrors')
                            if mirrors_div:
                                supervideo_link = mirrors_div.find('a', class_='mr', attrs={'data-link': True})
                                if supervideo_link:
                                    link_url = supervideo_link.get('data-link', '').strip()
                                    # Check if it's a supervideo link
                                    if 'supervideo' in link_url:
                                        supervideo_url = link_url
                        
                        # Only add episode if supervideo link is available and valid
                        if supervideo_url and supervideo_url != '#' and 'supervideo' in supervideo_url and current_season:
                            current_season.episodes.add({
                                'number': ep_num,
                                'name': ep_title,
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