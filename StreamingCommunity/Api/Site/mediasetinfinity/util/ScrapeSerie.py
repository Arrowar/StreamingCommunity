# 16.03.25


import logging
from urllib.parse import urlparse


# External libraries
from curl_cffi import requests
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.headers import get_headers, get_userAgent
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Api.Player.Helper.Vixcloud.util import SeasonManager


# Logic class
from .get_license import get_bearer_token


# Variable
max_timeout = config_manager.get_int("REQUESTS", "timeout")


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
        """Estrae l'ID della serie dall'URL di partenza"""
        self.serie_id = f"SE{self.url.split('SE')[1]}"
        print(f"Serie ID: {self.serie_id}")
        return self.serie_id

    def _get_public_id(self):
        """Ottiene il public ID tramite l'API watchlist"""
        bearer_token = get_bearer_token()
        headers = {
            'authorization': f'Bearer {bearer_token}',
            'user-agent': get_userAgent(),
        }

        response = requests.get(
            'https://api-ott-prod-fe.mediaset.net/PROD/play/userlist/watchlist/v2.0',
            headers=headers,
            impersonate="chrome",
            allow_redirects=True
        )

        if response.status_code == 401:
            print("Token scaduto, rinnovare il token")

        if response.status_code == 200:
            data = response.json()
            self.public_id = data['response']['entries'][0]['media'][0]['publicUrl'].split("/")[4]
            print(f"Public id: {self.public_id}")
            return self.public_id
        
        else:
            logging.error(f"Failed to get public ID: {response.status_code}")
            return None

    def _get_series_data(self):
        """Ottiene i dati della serie tramite l'API"""
        headers = {
            'User-Agent': get_userAgent(),
        }
        params = {'byGuid': self.serie_id}

        response = requests.get(
            f'https://feed.entertainment.tv.theplatform.eu/f/{self.public_id}/mediaset-prod-all-series-v2',
            params=params,
            headers=headers,
            impersonate="chrome",
            allow_redirects=True
        )
        print("Risposta per _get_series_data:", response.status_code)

        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to get series data: {response.status_code}")
            return None

    def _process_available_seasons(self, data):
        """Processa le stagioni disponibili dai dati della serie"""
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
                    'url': url,
                    'id': str(url).split("/")[-1],
                    'guid': season['guid']
                })
            else:
                logging.warning(f"Season URL not found: {url}")

        # Ordina le stagioni dalla più vecchia alla più nuova
        stagioni_disponibili.sort(key=lambda s: s['tvSeasonNumber'])
        
        return stagioni_disponibili

    def _build_season_page_urls(self, stagioni_disponibili):
        """Costruisce gli URL delle pagine delle stagioni"""
        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        series_slug = parsed_url.path.strip('/').split('/')[-1].split('_')[0]

        for season in stagioni_disponibili:
            page_url = f"{base_url}/fiction/{series_slug}/{series_slug}{season['tvSeasonNumber']}_{self.serie_id},{season['guid']}"
            season['page_url'] = page_url

    def _extract_season_sb_ids(self, stagioni_disponibili):
        """Estrae gli ID sb dalle pagine delle stagioni"""
        for season in stagioni_disponibili:
            response_page = requests.get(
                season['page_url'],
                headers={'User-Agent': get_userAgent()},
                impersonate="chrome",
                allow_redirects=True
            )
            print("Risposta per _extract_season_sb_ids:", response_page.status_code)

            soup = BeautifulSoup(response_page.text, 'html.parser')
            
            # Prova prima con 'Episodi', poi con 'Puntate intere'
            link = soup.find('a', string='Episodi')
            if not link:
                print("Using word: Puntate intere")
                link = soup.find('a', string='Puntate intere')
            
            if link and link.has_attr('href'):
                if not link.string == 'Puntate intere':
                    print("Using word: Episodi")
                season['sb'] = link['href'].split(',')[-1]
            else:
                logging.warning(f"Link 'Episodi' o 'Puntate intere' non trovato per stagione {season['tvSeasonNumber']}")

    def _get_season_episodes(self, season):
        """Ottiene gli episodi per una stagione specifica"""
        if not season.get('sb'):
            return

        episode_headers = {
            'origin': 'https://mediasetinfinity.mediaset.it',
            'referer': 'https://mediasetinfinity.mediaset.it/',
            'user-agent': get_userAgent(),
        }
        params = {
            'byCustomValue': "{subBrandId}{" + str(season["sb"].replace('sb', '')) + "}",
            'sort': ':publishInfo_lastPublished|asc,tvSeasonEpisodeNumber|asc',
            'range': '0-100',
        }
        episode_url = f"https://feed.entertainment.tv.theplatform.eu/f/{self.public_id}/mediaset-prod-all-programs-v2"

        episode_response = requests.get(episode_url, headers=episode_headers, params=params, impersonate="chrome"
                    , allow_redirects=True)
        print("Risposta per _get_season_episodes:", episode_response.status_code)
        
        if episode_response.status_code == 200:
            episode_data = episode_response.json()
            season['episodes'] = []
            
            for entry in episode_data.get('entries', []):
                episode_info = {
                    'id': entry.get('guid'),
                    'title': entry.get('title'),
                    'duration': int(entry.get('mediasetprogram$duration', 0) / 60) if entry.get('mediasetprogram$duration') else 0,
                    'url': entry.get('media', [{}])[0].get('publicUrl') if entry.get('media') else None
                }
                season['episodes'].append(episode_info)
            
            print(f"Found {len(season['episodes'])} episodes for season {season['tvSeasonNumber']}")
        else:
            logging.error(f"Failed to get episodes for season {season['tvSeasonNumber']}: {episode_response.status_code}")

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
                self._get_season_episodes(season)
                
            # Step 8: Populate seasons manager
            self._populate_seasons_manager()
            
        except Exception as e:
            logging.error(f"Error in collect_season: {str(e)}")

    def _populate_seasons_manager(self):
        """Popola il seasons_manager con i dati raccolti"""
        for season_data in self.stagioni_disponibili:
            season_obj = self.seasons_manager.add_season({
                'number': season_data['tvSeasonNumber'],
                'name': f"Stagione {season_data['tvSeasonNumber']}"
            })
            
            if season_obj and season_data.get('episodes'):
                for idx, episode in enumerate(season_data['episodes'], 1):
                    season_obj.episodes.add({
                        'id': episode['id'],
                        'number': idx,
                        'name': episode['title'],
                        'url': episode['url'],
                        'duration': episode['duration']
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