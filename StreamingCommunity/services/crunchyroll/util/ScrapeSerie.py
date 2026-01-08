# 16.03.25

import re
import logging
from typing import Dict, List, Optional, Tuple


# Internal utilities
from StreamingCommunity.services._base.object import SeasonManager


# Logic
from .client import CrunchyrollClient


# Constants
_EP_NUM_RE = re.compile(r"^\d+(\.\d+)?$")


def _fetch_api_seasons(series_id: str, client: CrunchyrollClient, params: Dict):
    """Fetch seasons from API."""
    url = f'{client.api_base_url}/content/v2/cms/series/{series_id}/seasons'
    return client.request('GET', url, params=params)


def _fetch_api_episodes(season_id: str, client: CrunchyrollClient, params: Dict):
    """Fetch episodes from API."""
    url = f'{client.api_base_url}/content/v2/cms/seasons/{season_id}/episodes'
    return client.request('GET', url, params=params)


def _extract_episode_number(episode_data: Dict) -> str:
    """Extract episode number from episode data."""
    meta = episode_data.get("episode_metadata") or {}
    candidates = [
        episode_data.get("episode"),
        meta.get("episode"),
        meta.get("episode_number"),
        episode_data.get("episode_number"),
    ]
    
    for val in candidates:
        if val is None:
            continue
        val_str = val.strip() if isinstance(val, str) else str(val)
        if val_str:
            return val_str
    return ""


def _is_special_episode(episode_number: str) -> bool:
    """Check if episode is a special."""
    if not episode_number:
        return True
    return not _EP_NUM_RE.match(episode_number)


def _assign_display_numbers(episodes: List[Dict]) -> List[Dict]:
    """Assign display numbers to episodes (normal and specials)."""
    ep_counter = 1
    sp_counter = 1
    
    for episode in episodes:
        if episode.get("is_special"):
            raw_label = episode.get("raw_episode")
            episode["display_number"] = f"SP{sp_counter}_{raw_label}" if raw_label else f"SP{sp_counter}"
            sp_counter += 1
        else:
            episode["display_number"] = str(ep_counter)
            ep_counter += 1
    
    return episodes


class GetSerieInfo:
    def __init__(self, series_id: str, *, locale: str = "it-IT", preferred_audio_language: str = "it-IT"):
        """Initialize series scraper with minimal API calls."""
        self.series_id = series_id
        self.seasons_manager = SeasonManager()
        self.client = CrunchyrollClient(locale=locale)
        
        self.params = {
            'force_locale': '',
            'preferred_audio_language': preferred_audio_language,
            'locale': locale,
        }
        self._episodes_cache = {}
        self._metadata_cache = {}

    def collect_season(self) -> None:
        """Collect all seasons for the series - SINGLE API CALL."""
        response = _fetch_api_seasons(self.series_id, self.client, self.params)
        
        if response.status_code != 200:
            logging.error(f"Failed to fetch seasons: {response.status_code}")
            return
        
        data = response.json()
        seasons = data.get("data", [])
        
        # Extract basic series name from first season
        if seasons:
            self.series_name = seasons[0].get("title")
        
        # Process seasons
        season_rows = []
        for season in seasons:
            raw_num = season.get("season_number", 0)
            season_rows.append({
                "id": season.get('id'),
                "title": season.get("title", f"Season {raw_num}"),
                "raw_number": int(raw_num or 0),
                "slug": season.get("slug", ""),
            })
        
        # Sort by number then title
        season_rows.sort(key=lambda r: (r["raw_number"], r["title"] or ""))
        
        # Add to manager
        for idx, row in enumerate(season_rows):
            self.seasons_manager.add_season({
                'number': row["raw_number"],
                'name': row["title"],
                'id': row["id"],
                'slug': row["slug"],
            })

    def _fetch_episodes_for_season(self, season_index: int) -> List[Dict]:
        """Fetch and cache episodes for a season - SINGLE API CALL per season."""
        season = self.seasons_manager.seasons[season_index-1]
        response = _fetch_api_episodes(season.id, self.client, self.params)
        
        # Get response json
        data = response.json()
        episodes_data = data.get("data", [])
        
        # Build episode list
        episodes = []
        for ep_data in episodes_data:
            ep_number = _extract_episode_number(ep_data)
            is_special = _is_special_episode(ep_number)
            ep_id = ep_data.get("id")
            
            # Cache metadata for later use
            if ep_id:
                self._metadata_cache[ep_id] = ep_data
            
            episodes.append({
                'id': ep_id,
                'number': ep_number,
                'is_special': is_special,
                'name': ep_data.get("title", f"Episodio {ep_data.get('episode_number')}"),
                'url': f"{self.client.web_base_url}/watch/{ep_id}",
                'duration': int(ep_data.get('duration_ms', 0) / 60000),
            })
        
        # Sort: normal episodes first, then specials
        normal = [e for e in episodes if not e.get("is_special")]
        specials = [e for e in episodes if e.get("is_special")]
        episodes = normal + specials
        
        # Assign display numbers
        episodes = _assign_display_numbers(episodes)
        
        # Cache and return
        self._episodes_cache[season_index] = episodes
        return episodes

    def _get_episode_audio_locales(self, episode_id: str) -> Tuple[List[str], Dict[str, str], Optional[str]]:
        """
        Get available audio locales WITHOUT calling playback API.
        Uses cached metadata from episode list API call.
        
        Returns:
            Tuple[List[str], Dict[str, str], Optional[str]]: (audio_locales, urls_by_locale, main_guid)
        """
        cached_data = self._metadata_cache.get(episode_id)
        
        if cached_data:
            meta = cached_data.get('episode_metadata', {}) or {}
            versions = meta.get("versions") or cached_data.get("versions") or []
            
            if versions:
                main_guid = None
                
                # First pass: find main track (for complete subtitles)
                for v in versions:
                    roles = v.get("roles", [])
                    if "main" in roles:
                        main_guid = v.get("guid")
                        break
                
                # Second pass: find preferred audio locale
                audio_locales = []
                urls_by_locale = {}
                seen_locales = set()
                
                for v in versions:
                    locale = v.get("audio_locale")
                    guid = v.get("guid")
                    if locale and guid and locale not in seen_locales:
                        seen_locales.add(locale)
                        audio_locales.append(locale)
                        urls_by_locale[locale] = f"{self.client.web_base_url}/watch/{guid}"
                
                if audio_locales:
                    return audio_locales, urls_by_locale, main_guid
    
        return [], {episode_id: f"{self.client.web_base_url}/watch/{episode_id}"}, None


    # ------------- FOR GUI -------------
    def getNumberSeason(self) -> int:
        """Get total number of seasons."""
        if not self.seasons_manager.seasons:
            self.collect_season()
        return len(self.seasons_manager.seasons)

    def getEpisodeSeasons(self, season_index: int) -> List[Dict]:
        """Get all episodes for a season."""
        if not self.seasons_manager.seasons:
            self.collect_season()
        
        if season_index not in self._episodes_cache:
            self._fetch_episodes_for_season(season_index)
        
        return self._episodes_cache.get(season_index, [])

    def selectEpisode(self, season_index: int, episode_index: int) -> Optional[Dict]:
        """Get specific episode with audio information."""
        episodes = self.getEpisodeSeasons(season_index)
        episode = episodes[episode_index]
        episode_id = episode.get("url", "").split("/")[-1] if episode.get("url") else None
        
        if not episode_id:
            return episode
        
        # Update URL to preferred language if available
        audio_locales, urls_by_locale, main_guid = self._get_episode_audio_locales(episode_id)
        
        # Store main_guid for complete subtitles access
        if main_guid:
            episode["main_guid"] = main_guid
            episode["main_url"] = f"{self.client.web_base_url}/watch/{main_guid}"
        
        # Continue with normal audio preference logic
        if urls_by_locale:
            preferred_lang = self.params.get("preferred_audio_language", "it-IT")
            new_url = urls_by_locale.get(preferred_lang) or urls_by_locale.get("en-US") or list(urls_by_locale.values())[0]
            if new_url:
                episode["url"] = new_url
        
        return episode