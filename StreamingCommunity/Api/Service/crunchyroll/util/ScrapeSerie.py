# 16.03.25

import re
from typing import Dict, List, Optional, Tuple


# Internal utilities
from StreamingCommunity.Api.Template.object import SeasonManager


# Logic
from .client import CrunchyrollClient
from .get_license import get_playback_session


# Variable
NORMALIZE_SEASON_NUMBERS = False
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


def _validate_duplicate_guids(client: CrunchyrollClient, locale_guids: Dict[str, List[str]], locale: str) -> Dict[str, str]:
    """Validate and clean up duplicate GUIDs for each locale."""
    cleaned = {}
    
    for loc, guids in locale_guids.items():
        if len(guids) == 1:
            cleaned[loc] = guids[0]
            continue
        
        # Validate each GUID
        valid_guids = []
        for guid in guids:
            try:
                check_url = f"{client.api_base_url}/content/v2/cms/episodes/{guid}"
                check_params = {"ratings": "true", "locale": locale}
                resp = client.request("GET", check_url, params=check_params, _retries=2)
                if resp.status_code == 200:
                    valid_guids.append(guid)
            except Exception:
                continue
        
        # Use first valid or first available
        cleaned[loc] = valid_guids[0] if valid_guids else guids[0]
    
    return cleaned


class GetSerieInfo:
    def __init__(self, series_id: str, *, locale: str = "it-IT", preferred_audio_language: str = "it-IT", qps: Optional[float] = None):
        """Initialize series scraper."""
        self.series_id = series_id
        self.seasons_manager = SeasonManager()
        
        self.client = CrunchyrollClient(qps=qps, locale=locale)
        if not self.client.start():
            raise Exception("Failed to authenticate with Crunchyroll")
        
        self.params = {
            'force_locale': '',
            'preferred_audio_language': preferred_audio_language,
            'locale': locale,
        }
        self._episodes_cache = {}
        self.normalize_seasons = NORMALIZE_SEASON_NUMBERS

    def collect_season(self) -> None:
        """Collect all seasons for the series."""
        response = _fetch_api_seasons(self.series_id, self.client, self.params)
        
        if response.status_code != 200:
            return
        
        data = response.json()
        seasons = data.get("data", [])
        
        # Extract series metadata from first season
        if seasons:
            self._extract_series_metadata(seasons[0])
        
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
        if self.normalize_seasons:
            for i, row in enumerate(season_rows, start=1):
                self.seasons_manager.add_season({
                    'number': i,
                    'cr_number': row["raw_number"],
                    'name': row["title"],
                    'id': row["id"],
                    'slug': row["slug"],
                })
        else:
            for row in season_rows:
                self.seasons_manager.add_season({
                    'number': row["raw_number"],
                    'name': row["title"],
                    'id': row["id"],
                    'slug': row["slug"],
                })

    def _extract_series_metadata(self, first_season: Dict) -> None:
        """Extract series name and description from first season."""
        series_meta = first_season.get("series_metadata") or {}
        
        self.series_name = (
            first_season.get("series_title")
            or series_meta.get("title")
            or series_meta.get("name")
            or first_season.get("title")
        )
        
        self.series_description = (
            first_season.get("description")
            or first_season.get("series_description")
            or series_meta.get("description")
        )

    def _fetch_episodes_for_season(self, season_index: int) -> List[Dict]:
        """Fetch and cache episodes for a season."""
        season = self.seasons_manager.get_season_by_number(season_index)
        if not season:
            return []
        
        response = _fetch_api_episodes(season.id, self.client, self.params)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        episodes_data = data.get("data", [])
        
        # Build episode list
        episodes = []
        for ep_data in episodes_data:
            ep_number = _extract_episode_number(ep_data)
            is_special = _is_special_episode(ep_number)
            
            episodes.append({
                'id': ep_data.get("id"),
                'number': ep_data.get("episode_number"),
                'raw_episode': ep_number or None,
                'is_special': is_special,
                'name': ep_data.get("title", f"Episodio {ep_data.get('episode_number')}"),
                'url': f"{self.client.web_base_url}/watch/{ep_data.get('id')}",
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

    def _get_episode_audio_locales(self, episode_id: str) -> Tuple[List[str], Dict[str, str]]:
        """Get available audio locales and their URLs."""
        url = f'{self.client.api_base_url}/content/v2/cms/objects/{episode_id}'
        params = {'ratings': 'true', 'locale': self.params.get('locale')}
        
        response = self.client.request('GET', url, params=params)
        
        if response.status_code != 200:
            return self._fallback_audio_detection(episode_id)
        
        data = response.json()
        item = (data.get("data") or [{}])[0] or {}
        meta = item.get('episode_metadata', {}) or {}
        versions = meta.get("versions") or item.get("versions") or []
        
        if not versions:
            return self._fallback_audio_detection(episode_id)
        
        # Extract locale-GUID pairs
        locale_guid_pairs = []
        for v in versions:
            locale = v.get("audio_locale")
            guid = v.get("guid")
            if locale and guid:
                locale_guid_pairs.append((locale, guid))
        
        if not locale_guid_pairs:
            return self._fallback_audio_detection(episode_id)
        
        # Group GUIDs by locale
        locale_guids = {}
        for locale, guid in locale_guid_pairs:
            locale_guids.setdefault(locale, [])
            if guid not in locale_guids[locale]:
                locale_guids[locale].append(guid)
        
        # Validate duplicates
        cleaned_guids = _validate_duplicate_guids(self.client, locale_guids, self.params.get("locale"))
        
        # Build result maintaining order
        audio_locales = []
        urls_by_locale = {}
        seen_locales = set()
        
        for locale, _ in locale_guid_pairs:
            if locale in seen_locales:
                continue
            seen_locales.add(locale)
            
            guid = cleaned_guids.get(locale)
            if guid:
                audio_locales.append(locale)
                urls_by_locale[locale] = f"{self.client.web_base_url}/watch/{guid}"
        
        # Print available audio languages
        if audio_locales:
            print(f"\n[INFO] Available audio languages: {', '.join(audio_locales)}")
        
        return audio_locales, urls_by_locale

    def _fallback_audio_detection(self, episode_id: str) -> Tuple[List[str], Dict[str, str]]:
        """Fallback method to detect audio locale."""
        try:
            _, _, _, _, audio_locale = get_playback_session(self.client, episode_id)
            
            if audio_locale:
                return [audio_locale], {audio_locale: f"{self.client.web_base_url}/watch/{episode_id}"}
        except Exception:
            pass
        
        return [], {}

    
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
        
        if not episodes or episode_index < 0 or episode_index >= len(episodes):
            return None
        
        episode = episodes[episode_index]
        episode_id = episode.get("url", "").split("/")[-1] if episode.get("url") else None
        
        if not episode_id:
            return episode
        
        # Add audio locale information
        audio_locales, urls_by_locale = self._get_episode_audio_locales(episode_id)
        episode["audio_locales"] = audio_locales
        episode["watch_urls_by_audio"] = urls_by_locale
        
        # Update URL to preferred language
        preferred_lang = self.params.get("preferred_audio_language", "it-IT")
        new_url = urls_by_locale.get(preferred_lang) or urls_by_locale.get("en-US")
        if new_url:
            episode["url"] = new_url
        
        return episode