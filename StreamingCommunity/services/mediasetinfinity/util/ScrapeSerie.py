# 16.03.25

import re
import json
import logging
from urllib.parse import urlparse, quote

# External libraries
from bs4 import BeautifulSoup

# Internal utilities
from StreamingCommunity.utils.http_client import create_client, get_userAgent, get_headers
from StreamingCommunity.services._base.object import SeasonManager


class GetSerieInfo:
    def __init__(self, url):
        """
        Initialize the GetSerieInfo class for scraping TV series information.
        
        Args:
            - url (str): The URL of the streaming site.
        """
        self.headers = get_headers()
        self.url = url
        self.seasons_manager = SeasonManager()
        self.serie_id = None
        self.public_id = None
        self.series_name = ""
        self.stagioni_disponibili = []

    def _extract_serie_id(self):
        """Extract the series ID from the starting URL"""
        self.serie_id = f"SE{self.url.split('SE')[1]}"
        return self.serie_id

    def _get_public_id(self):
        """Get the public ID for API calls"""
        self.public_id = "PR1GhC"
        return self.public_id

    def _get_series_data(self):
        """Get series data through the API"""
        try:
            params = {'byGuid': self.serie_id}
            response = create_client(headers=self.headers).get(f'https://feed.entertainment.tv.theplatform.eu/f/{self.public_id}/mediaset-prod-all-series-v2', params=params)
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            logging.error(f"Failed to get series data with error: {e}")
            return None

    def _process_available_seasons(self, data):
        """Process available seasons from series data"""
        if not data or not data.get('entries'):
            logging.error("No series data found")
            return []

        entry = data['entries'][0]
        self.series_name = entry.get('title', '')
        
        seriesTvSeasons = entry.get('seriesTvSeasons', [])
        availableTvSeasonIds = entry.get('availableTvSeasonIds', [])

        stagioni_disponibili = []

        for url in availableTvSeasonIds:
            season = next((s for s in seriesTvSeasons if s['id'] == url), None)
            if season:
                stagioni_disponibili.append({
                    'tvSeasonNumber': season['tvSeasonNumber'],
                    'title': season.get('title', ''),
                    'url': url,
                    'id': str(url).split("/")[-1],
                    'guid': season['guid']
                })
                
            else:
                logging.warning(f"Season URL not found: {url}")

        # Sort seasons from oldest to newest
        stagioni_disponibili.sort(key=lambda s: s['tvSeasonNumber'])
        
        return stagioni_disponibili

    def _build_season_page_urls(self, stagioni_disponibili):
        """Build season page URLs"""
        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        series_slug = parsed_url.path.strip('/').split('/')[-1].split('_')[0]

        for season in stagioni_disponibili:
            page_url = f"{base_url}/fiction/{series_slug}/{series_slug}{season['tvSeasonNumber']}_{self.serie_id},{season['guid']}"
            season['page_url'] = page_url

    def _extract_season_sb_ids(self, stagioni_disponibili):
        """Extract sb IDs from season pages"""
        client = create_client()
        
        for season in stagioni_disponibili:
            response_page = client.get(season['page_url'], headers={'User-Agent': get_userAgent()})
            
            print("Response for _extract_season_sb_ids:", response_page.status_code, " season index:", season['tvSeasonNumber'])
            soup = BeautifulSoup(response_page.text, 'html.parser')
            
            # Check for titleCarousel links (multiple categories)
            carousel_links = soup.find_all('a', class_='titleCarousel')
            
            if carousel_links:
                print(f"Found {len(carousel_links)} titleCarousel categories")
                season['categories'] = []
                
                for carousel_link in carousel_links:
                    if carousel_link.has_attr('href'):
                        category_title = carousel_link.find('h2')
                        category_name = category_title.text.strip() if category_title else 'Unnamed'
                        href = carousel_link['href']
                        if ',' in href:
                            sb_id = href.split(',')[-1]
                        else:
                            sb_id = href.split('_')[-1]

                        season['categories'].append({
                            'name': category_name,
                            'sb': sb_id
                        })
            else:
                logging.warning(f"No titleCarousel categories found for season {season['tvSeasonNumber']}")

    def _get_season_episodes(self, season, sb_id, category_name):
        """Get episodes for a specific season"""
        episode_headers = {
            'user-agent': get_userAgent(),
        }
        
        # Check if sb_id is numeric (with sb prefix) or alphanumeric
        if sb_id.startswith('sb'):
            clean_sb_id = sb_id[2:]
            
            params = {
                'byCustomValue': "{subBrandId}{" + str(clean_sb_id) + "}",
                'sort': ':publishInfo_lastPublished|asc,tvSeasonEpisodeNumber|asc',
                'range': '0-100',
            }
            episode_url = f"https://feed.entertainment.tv.theplatform.eu/f/{self.public_id}/mediaset-prod-all-programs-v2"
            
            try:
                episode_response = create_client(headers=episode_headers).get(episode_url, params=params)
                episode_response.raise_for_status()
                
                episode_data = episode_response.json()
                episodes = []
                
                for entry in episode_data.get('entries', []):
                    duration = int(entry.get('mediasetprogram$duration', 0) / 60) if entry.get('mediasetprogram$duration') else 0
                    
                    episode_info = {
                        'id': entry.get('guid'),
                        'title': entry.get('title'),
                        'duration': duration,
                        'url': entry.get('media', [{}])[0].get('publicUrl') if entry.get('media') else None,
                        'name': entry.get('title'),
                        'category': category_name
                    }
                    episodes.append(episode_info)
                
                print(f"Found {len(episodes)} episodes for season {season['tvSeasonNumber']} ({category_name})")
                return episodes
                
            except Exception as e:
                logging.error(f"Failed to get episodes for season {season['tvSeasonNumber']} with error: {e}")
                return []
        
        else:
            category_slug = category_name.lower().replace(' ', '-').replace("'", "").replace("à", "a").replace("è", "e").replace("ì", "i").replace("ò", "o").replace("ù", "u")
            browse_url = f"https://mediasetinfinity.mediaset.it/browse/{category_slug}_{sb_id}"
            
            # Create the router state
            url_path = browse_url.split('mediasetinfinity.mediaset.it/')[1] if 'mediasetinfinity.mediaset.it/' in browse_url else browse_url
            state = ["", {"children": [["path", url_path, "c"], {"children": ["__PAGE__", {}, None, "refetch"]}, None, None]}, None, None]
            router_state_tree = quote(json.dumps(state, separators=(',', ':')))

            rsc_headers = {
                'rsc': '1',
                'next-router-state-tree': router_state_tree,
                'User-Agent': get_userAgent()
            }
            try:
                episode_response = create_client(headers=rsc_headers).get(browse_url)
                episode_response.raise_for_status()
                
                episodes = self._extract_episodes_from_rsc_text(episode_response.text, category_name)
                print(f"Found {len(episodes)} episodes for season {season['tvSeasonNumber']} ({category_name})")
                return episodes
                
            except Exception as e:
                logging.error(f"Failed to get episodes for season {season['tvSeasonNumber']} with error: {e}")
                return []

    def _extract_episodes_from_rsc_text(self, text, category_name):
        """Extract episodes from RSC response text"""
        episodes = []
        pattern = r'"__typename":"VideoItem".*?"url":"https://mediasetinfinity\.mediaset\.it/video/[^"]*?"'
        
        for match in re.finditer(pattern, text, re.DOTALL):
            block = match.group(0)
            ep = {}
            fields = {
                'title': r'"cardTitle":"([^"]*?)"',
                'description': r'"description":"([^"]*?)"',
                'duration': r'"duration":(\d+)',
                'guid': r'"guid":"([^"]*?)"',
                'url': r'"url":"(https://mediasetinfinity\.mediaset\.it/video/[^"]*?)"'
            }
            
            for key, regex in fields.items():
                m = re.search(regex, block)
                if m:
                    ep[key] = int(m.group(1)) if key == 'duration' else m.group(1)
            
            if ep:
                episode_info = {
                    'id': ep.get('guid', ''),
                    'title': ep.get('title', ''),
                    'duration': int(ep.get('duration', 0) / 60) if ep.get('duration') else 0,
                    'url': ep.get('url', ''),
                    'name': ep.get('title', ''),
                    'category': category_name,
                    'description': ep.get('description', ''),
                    'series': ''
                }
                episodes.append(episode_info)
        
        return episodes

    def collect_season(self) -> None:
        """
        Retrieve all episodes for all seasons using the new Mediaset Infinity API.
        """
        try:
            # Step 1: Extract serie ID from URL
            self._extract_serie_id()
            
            # Step 2: Get public ID
            if not self._get_public_id():
                logging.error("Failed to get public ID")
                return
                
            # Step 3: Get series data
            data = self._get_series_data()
            if not data:
                logging.error("Failed to get series data")
                return
                
            # Step 4: Process available seasons
            self.stagioni_disponibili = self._process_available_seasons(data)
            if not self.stagioni_disponibili:
                logging.error("No seasons found")
                return
                
            # Step 5: Build season page URLs
            self._build_season_page_urls(self.stagioni_disponibili)
            
            # Step 6: Extract sb IDs from season pages
            self._extract_season_sb_ids(self.stagioni_disponibili)
            
            # Step 7: Get episodes for each season
            for season in self.stagioni_disponibili:
                if 'categories' in season:
                    season['episodes'] = []
                    for category in season['categories']:
                        episodes = self._get_season_episodes(season, category['sb'], category['name'])
                        if episodes:
                            season['episodes'].extend(episodes)
                
            # Step 8: Populate seasons manager
            self._populate_seasons_manager()
            
        except Exception as e:
            logging.error(f"Error in collect_season: {str(e)}")

    def _populate_seasons_manager(self):
        """Populate the seasons_manager with collected data - ONLY for seasons with episodes"""
        seasons_with_episodes = 0
        
        for season_data in self.stagioni_disponibili:
            
            # Add season to manager ONLY if it has episodes
            if season_data.get('episodes') and len(season_data['episodes']) > 0:
                season_obj = self.seasons_manager.add_season({
                    'number': season_data['tvSeasonNumber'],
                    'name': f"Season {season_data['tvSeasonNumber']}",
                    'id': season_data.get('title', '')
                })
                
                if season_obj:
                    for episode in season_data['episodes']:
                        season_obj.episodes.add(episode)
                    seasons_with_episodes += 1
        
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
        
        # Convert 1-based user input to 0-based array index
        season_index = season_number - 1
        
        # Get season by index in the available seasons list
        season = self.seasons_manager.seasons[season_index]
        
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