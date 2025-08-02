# 16.03.25

import logging


# External libraries
from curl_cffi import requests


# Internal utilities
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Api.Player.Helper.Vixcloud.util import SeasonManager
from .get_license import get_auth_token, generate_device_id


# Variable
max_timeout = config_manager.get_int("REQUESTS", "timeout")


def get_series_seasons(series_id, headers, params):
    """
    Fetches the seasons for a given series ID from Crunchyroll.
    """
    url = f'https://www.crunchyroll.com/content/v2/cms/series/{series_id}/seasons'
    response = requests.get(
        url,
        params=params,
        headers=headers,
        impersonate="chrome110"
    )
    return response


def get_season_episodes(season_id, headers, params):
    """
    Fetches the episodes for a given season ID from Crunchyroll.
    """
    url = f'https://www.crunchyroll.com/content/v2/cms/seasons/{season_id}/episodes'
    response = requests.get(
        url,
        params=params,
        headers=headers,
        impersonate="chrome110"
    )
    return response


class GetSerieInfo:
    def __init__(self, series_id):
        """
        Initialize the GetSerieInfo class for scraping TV series information using Crunchyroll API.
        
        Args:
            - series_id (str): The Crunchyroll series ID.
        """
        self.series_id = series_id
        self.seasons_manager = SeasonManager()
        self.headers = get_headers()
        self.headers['authorization'] = f"Bearer {get_auth_token(generate_device_id()).access_token}"
        self.params = {
            'force_locale': '',
            'preferred_audio_language': 'it-IT',
            'locale': 'it-IT',
        }
        self.series_name = None
        self._episodes_cache = {}

    def collect_season(self) -> None:
        """
        Retrieve all seasons using Crunchyroll API, but NOT episodes.
        """
        response = get_series_seasons(self.series_id, self.headers, self.params)

        if response.status_code != 200:
            logging.error(f"Failed to fetch seasons for series {self.series_id}")
            return

        # Get the JSON response 
        data = response.json()
        seasons = data.get("data", [])

        # Set series name from first season if available
        if seasons:
            self.series_name = seasons[0].get("series_title") or seasons[0].get("title")

        for season in seasons:
            season_num = season.get("season_number", 0)
            season_name = season.get("title", f"Season {season_num}")

            self.seasons_manager.add_season({
                'number': season_num,
                'name': season_name,
                'id': season.get('id')
            })

    def _fetch_episodes_for_season(self, season_number: int):
        """
        Fetch and cache episodes for a specific season number.
        """
        season = self.seasons_manager.get_season_by_number(season_number)

        if not season or getattr(season, 'id', None) is None:
            logging.error(f"Season {season_number} not found or missing id.")
            return []

        season_id = season.id
        ep_response = get_season_episodes(season_id, self.headers, self.params)
        if ep_response.status_code != 200:
            logging.error(f"Failed to fetch episodes for season {season_id}")
            return []

        ep_data = ep_response.json()
        episodes = ep_data.get("data", [])
        episode_list = []

        for ep in episodes:
            ep_num = ep.get("episode_number")
            ep_title = ep.get("title", f"Episodio {ep_num}")
            ep_id = ep.get("id")
            ep_url = f"https://www.crunchyroll.com/watch/{ep_id}"
            
            episode_list.append({
                'number': ep_num,
                'name': ep_title,
                'url': ep_url,
                'duration': int(ep.get('duration_ms', 0) / 60000),
            })
            
        self._episodes_cache[season_number] = episode_list
        return episode_list

    def _get_episode_audio_locales_and_urls(self, episode_id):
        """
        Fetch available audio locales and their URLs for a given episode ID.
        Returns: (audio_locales, urls_by_locale)
        """
        url = f'https://www.crunchyroll.com/content/v2/cms/objects/{episode_id}'
        headers = self.headers.copy()
        params = {
            'ratings': 'true',
            'locale': 'it-IT',
        }
        response = requests.get(
            url,
            params=params,
            headers=headers,
            impersonate="chrome110"
        )

        if response.status_code != 200:
            logging.warning(f"Failed to fetch audio locales for episode {episode_id}")
            return [], {}
        
        data = response.json()
        try:
            versions = data["data"][0]['episode_metadata'].get("versions", [])

            audio_locales = []
            urls_by_locale = {}

            for v in versions:
                locale = v.get("audio_locale")
                guid = v.get("guid")

                if locale and guid:
                    audio_locales.append(locale)
                    urls_by_locale[locale] = f"https://www.crunchyroll.com/it/watch/{guid}"
                    #print(f"Locale: {locale}, URL: {urls_by_locale[locale]}")

            return audio_locales, urls_by_locale
        
        except Exception as e:
            logging.error(f"Error parsing audio locales for episode {episode_id}: {e}")
            return [], {}

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
        Get all episodes for a specific season (fetches only when needed).
        """
        if not self.seasons_manager.seasons:
            self.collect_season()
        if season_number not in self._episodes_cache:
            episodes = self._fetch_episodes_for_season(season_number)
        else:
            episodes = self._episodes_cache[season_number]
        return episodes

    def selectEpisode(self, season_number: int, episode_index: int) -> dict:
        """
        Get information for a specific episode in a specific season.
        """
        episodes = self.getEpisodeSeasons(season_number)
        if not episodes or episode_index < 0 or episode_index >= len(episodes):
            logging.error(f"Episode index {episode_index} is out of range for season {season_number}")
            return None

        episode = episodes[episode_index]
        episode_id = episode.get("url", "").split("/")[-1] if "url" in episode else None

        # Update only the episode URL if available in it-IT or en-US
        _, urls_by_locale = self._get_episode_audio_locales_and_urls(episode_id)
        new_url = urls_by_locale.get("it-IT") or urls_by_locale.get("en-US")

        if new_url:
            episode["url"] = new_url

        return episode