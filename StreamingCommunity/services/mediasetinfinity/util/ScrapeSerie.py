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
        self.client = create_client()
        self.seasons_manager = SeasonManager()
        self.serie_id = None
        self.public_id = None
        self.series_name = ""
        self.stagioni_disponibili = []

    def _extract_serie_id(self):
        """Extract the series ID from the starting URL"""
        try:
            after = self.url.split('SE', 1)[1]
            after = after.split(',')[0].strip()
            self.serie_id = f"SE{after}"
            return self.serie_id
        except Exception as e:
            logging.error(f"Failed to extract serie id from url {self.url}: {e}")
            self.serie_id = None
            return None

    def _get_public_id(self):
        """Get the public ID for API calls"""
        self.public_id = "PR1GhC"
        return self.public_id

    def _get_series_data(self):
        """Get series data through the API"""
        try:
            params = {'byGuid': self.serie_id}
            url = f'https://feed.entertainment.tv.theplatform.eu/f/{self.public_id}/mediaset-prod-all-series-v2'
            data = self.client.get(url, params=params, headers=self.headers)
            return data.json()
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
        for season in stagioni_disponibili:
            response_page = self.client.get(season['page_url'], headers={'User-Agent': get_userAgent()})
            
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
                episode_response = self.client.get(episode_url, params=params, headers=episode_headers)
                status = getattr(episode_response, 'status_code', None)
                if status and status >= 400:
                    episode_response.raise_for_status()

                try:
                    episode_data = episode_response.json()
                except Exception:
                    episode_data = json.loads(episode_response.text)
                
                episodes = []
                
                for entry in episode_data.get('entries', []):
                    duration = int(entry.get('mediasetprogram$duration', 0) / 60) if entry.get('mediasetprogram$duration') else 0
                    
                    episode_info = {
                        'id': entry.get('guid'),
                        'title': entry.get('title'),
                        'duration': duration,
                        'url': entry.get('media', [{}])[0].get('publicUrl') if entry.get('media') else None,
                        'name': entry.get('title'),
                        'category': category_name,
                        'tvSeasonEpisodeNumber': entry.get('tvSeasonEpisodeNumber') or entry.get('mediasetprogram$episodeNumber')
                    }
                    episodes.append(episode_info)
                
                print(f"Found {len(episodes)} episodes for season {season['tvSeasonNumber']} ({category_name})")
                return episodes
                
            except Exception as e:
                logging.error(f"Failed to get episodes for season {season['tvSeasonNumber']} with error: {e}")
                return []
        
        else:
            # Non-sb categories: fallback to browse/rsc parsing
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
                episode_response = self.client.get(browse_url, headers=rsc_headers)
                status = getattr(episode_response, 'status_code', None)
                if status and status >= 400:
                    episode_response.raise_for_status()

                episodes = self._extract_episodes_from_rsc_text(episode_response.text, category_name)
                
                print(f"Found {len(episodes)} episodes for season {season['tvSeasonNumber']} ({category_name})")
                return episodes
            
            except Exception as e:
                logging.error(f"Failed to get episodes for season {season['tvSeasonNumber']} with error: {e}")
                return []

    def _get_all_season_episodes(self, season):
        """Fetch the full programs feed for the season and return cleaned episode list."""
        try:
            programs_url = f"https://feed.entertainment.tv.theplatform.eu/f/{self.public_id}/mediaset-prod-all-programs-v2"
            params = {
                'byTvSeasonId': season.get('url') or season.get('id'),
                'range': '0-99',
                'sort': ':publishInfo_lastPublished|asc,tvSeasonEpisodeNumber|asc'
            }
            data = self.client.get(programs_url, params=params, headers={'user-agent': get_userAgent()}).json()
            if not data:
                return []

            episodes = []
            for entry in data.get('entries', []):
                duration = int(entry.get('mediasetprogram$duration', 0) / 60) if entry.get('mediasetprogram$duration') else 0
                episodes.append({
                    'id': entry.get('guid'),
                    'title': entry.get('title'),
                    'duration': duration,
                    'url': entry.get('media', [{}])[0].get('publicUrl') if entry.get('media') else None,
                    'name': entry.get('title'),
                    'tvSeasonEpisodeNumber': entry.get('tvSeasonEpisodeNumber') or entry.get('mediasetprogram$episodeNumber'),
                    'category': 'programs_feed',
                    'description': entry.get('description', '')
                })

            # Filter out obvious non-episode items
            bad_words = [
                'trailer', 'Trailer', 'promo', 'Promo', 'teaser', 'Teaser', 'clip', 'Clip', 'backstage', 'Backstage', 'making of', 'making-of',
                'galleria', 'Galleria', 'scene', 'Scene', 'dietro le quinte', 'recap', 'Recap', 'estratto', 'Estratto', 'extra', 'Extra'
            ]

            filtered = []
            seen = set()
            for ep in episodes:
                gid = ep.get('id') or ep.get('url') or ep.get('title')
                if not gid or gid in seen:
                    continue

                title = (ep.get('title') or '').lower()
                # drop if title indicates promo/trailer
                if any(w in title for w in bad_words):
                    continue

                dur = ep.get('duration') or 0
                has_num = bool(ep.get('tvSeasonEpisodeNumber'))

                # Keep if it has an explicit episode number, or looks like an episode
                if has_num or 'episod' in title or dur >= 15:
                    filtered.append(ep)
                    seen.add(gid)

            # Sort by episode number when available
            try:
                filtered.sort(key=lambda e: int(e.get('tvSeasonEpisodeNumber') or 0))
            except Exception:
                pass

            return filtered
        except Exception as e:
            logging.warning(f"_get_all_season_episodes failed for season {season.get('tvSeasonNumber')}: {e}")
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

            # Step 7: Prefer a single full-season programs feed per season
            for season in self.stagioni_disponibili:
                season['episodes'] = []
                
                # Try full-season programs feed once
                full = self._get_all_season_episodes(season)
                if full:
                    season['episodes'] = full

                    # Map episodes to carousel categories
                    ep_map = {}
                    for ep in season['episodes']:
                        gid = ep.get('id') or ep.get('url') or ep.get('title')
                        if gid:
                            ep_map[gid] = ep

                    if 'categories' in season:
                        for category in season['categories']:
                            try:
                                cat_eps = self._get_season_episodes(season, category['sb'], category['name'])
                                for cep in cat_eps:
                                    gid = cep.get('id') or cep.get('url') or cep.get('title')
                                    if not gid:
                                        continue
                                    if gid in ep_map:
                                        e = ep_map[gid]
                                        cats = e.get('categories') or []
                                        if category['name'] not in cats:
                                            cats.append(category['name'])
                                        e['categories'] = cats
                                        e['category'] = cats[0] if cats else e.get('category', 'programs_feed')
                            except Exception:
                                continue
                else:
                    # Fallback: collect per-category
                    if 'categories' in season:
                        for category in season['categories']:
                            episodes = self._get_season_episodes(season, category['sb'], category['name'])
                            if episodes:
                                for ep in episodes:
                                    if ep.get('id') not in [x.get('id') for x in season['episodes']]:
                                        season['episodes'].append(ep)
            
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
            
        # Try to find a season object whose `.number` matches the requested season_number
        available_numbers = [s.number for s in self.seasons_manager.seasons]

        for s in self.seasons_manager.seasons:
            if s.number == season_number:
                return s.episodes.episodes

        # Fallback: treat the input as a 1-based index into the seasons list (legacy behavior)
        idx = season_number - 1
        if 0 <= idx < len(self.seasons_manager.seasons):
            return self.seasons_manager.seasons[idx].episodes.episodes

        # If we still can't find it, log and return empty list instead of raising
        logging.error(f"Season {season_number} not found. Available seasons: {available_numbers}")
        return []
        
    def selectEpisode(self, season_number: int, episode_index: int) -> dict:
        """
        Get information for a specific episode in a specific season.
        """
        episodes = self.getEpisodeSeasons(season_number)
        if not episodes or episode_index < 0 or episode_index >= len(episodes):
            logging.error(f"Episode index {episode_index} is out of range for season {season_number}")
            return None
            
        return episodes[episode_index]
