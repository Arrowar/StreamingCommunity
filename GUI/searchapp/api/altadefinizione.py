# 27-01-26


import importlib
from typing import List, Optional


# Internal utilities
from .base import BaseStreamingAPI, MediaItem, Season, Episode


# External utilities
from StreamingCommunity.utils import config_manager
from StreamingCommunity.services._base.site_loader import get_folder_name
from StreamingCommunity.services.altadefinizione.scrapper import GetSerieInfo


class AltadefinzioneAPI(BaseStreamingAPI):
    def __init__(self):
        super().__init__()
        self.site_name = "altadefinizione"
        self._load_config()
        self._search_fn = None
    
    def _load_config(self):
        """Load site configuration."""
        self.base_url = config_manager.domain.get(self.site_name, "full_url")
        print(f"[{self.site_name}] Configuration loaded: base_url={self.base_url}")
    
    def _get_search_fn(self):
        """Lazy load the search function."""
        if self._search_fn is None:
            module = importlib.import_module(f"StreamingCommunity.{get_folder_name()}.{self.site_name}")
            self._search_fn = getattr(module, "search")
        return self._search_fn
    
    def search(self, query: str) -> List[MediaItem]:
        """
        Search for content on Altadefinizione.
        
        Args:
            query: Search term
            
        Returns:
            List of MediaItem objects
        """
        search_fn = self._get_search_fn()
        database = search_fn(query, get_onlyDatabase=True)
        
        results = []
        if database and hasattr(database, 'media_list'):
            for element in database.media_list:
                item_dict = element.__dict__.copy() if hasattr(element, '__dict__') else {}
                
                media_item = MediaItem(
                    url=item_dict.get('url'),
                    name=item_dict.get('name'),
                    type=item_dict.get('type'),
                    poster=item_dict.get('image'),
                    raw_data=item_dict
                )
                results.append(media_item)
        
        return results

    def get_series_metadata(self, media_item: MediaItem) -> Optional[List[Season]]:
        """
        Get seasons and episodes for an Altadefinizione series.
        
        Args:
            media_item: MediaItem to get metadata for
            
        Returns:
            List of Season objects, or None if not a series
        """
        # Check if it's a movie (URL contains "/film/" instead of "/serie-tv/")
        if media_item.is_movie or "/film/" in media_item.url:
            return None
        
        scrape_serie = GetSerieInfo(media_item.url)
        seasons_count = scrape_serie.getNumberSeason()
        
        if not seasons_count:
            print(f"[Altadefinizione] No seasons found for: {media_item.name}")
            return None
    
        seasons = []
        for s in scrape_serie.seasons_manager.seasons:
            season_num = s.number
            season_name = getattr(s, 'name', None)
            
            episodes_raw = scrape_serie.getEpisodeSeasons(season_num)
            episodes = []
            
            for idx, ep in enumerate(episodes_raw or [], 1):
                episode = Episode(
                    number=getattr(ep, "number", idx),
                    name=getattr(ep, 'name', f"Episodio {idx}"),
                    id=getattr(ep, 'url', None)
                )
                episodes.append(episode)
            
            season = Season(number=season_num, episodes=episodes, name=season_name)
            seasons.append(season)
            print(f"[Altadefinizione] Season {season_num} ({season_name}): {len(episodes)} episodes")
        
        return seasons if seasons else None
    
    def start_download(self, media_item: MediaItem, season: Optional[str] = None, episodes: Optional[str] = None) -> bool:
        """
        Start downloading from Altadefinizione.
        
        Args:
            media_item: MediaItem to download
            season: Season number (for series)
            episodes: Episode selection
            
        Returns:
            True if download started successfully
        """
        search_fn = self._get_search_fn()
        
        # Prepare direct_item from MediaItem
        direct_item = media_item.raw_data or media_item.to_dict()
        
        # Prepare selections
        selections = None
        if season or episodes:
            selections = {
                'season': season,
                'episode': episodes
            }
        
        # Execute download
        search_fn(direct_item=direct_item, selections=selections)
        return True