# 27.01.26


import importlib
from typing import List, Optional


# Internal utilities
from .base import BaseStreamingAPI, MediaItem, Season, Episode


# External utilities
from StreamingCommunity.services._base.site_loader import get_folder_name
from StreamingCommunity.services.realtime.scrapper import GetSerieInfo


class NoveAPI(BaseStreamingAPI):
    def __init__(self):
        super().__init__()
        self.site_name = "nove"
        self._load_config()
        self._search_fn = None
    
    def _load_config(self):
        """Load site configuration."""
        self.base_url = "https://public.aurora.enhanced.live"
    
    def _get_search_fn(self):
        """Lazy load the search function."""
        if self._search_fn is None:
            module = importlib.import_module(f"StreamingCommunity.{get_folder_name()}.{self.site_name}")
            self._search_fn = getattr(module, "search")
        return self._search_fn
    
    def search(self, query: str) -> List[MediaItem]:
        """
        Search for content on Nove.
        
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
                    name=item_dict.get('name'),
                    type=item_dict.get('type', 'tv'),
                    url=item_dict.get('url'),
                    poster=item_dict.get('image'),
                    year=item_dict.get('year'),
                    raw_data=item_dict
                )
                results.append(media_item)
        
        return results
    
    def get_series_metadata(self, media_item: MediaItem) -> Optional[List[Season]]:
        """
        Get seasons and episodes for a Nove series.
        
        Args:
            media_item: MediaItem to get metadata for
            
        Returns:
            List of Season objects, or None if not a series
        """
        if media_item.is_movie:
            return None
        
        scrape_serie = GetSerieInfo(media_item.url)
        scrape_serie.getNumberSeason()
        seasons_count = len(scrape_serie.seasons_manager)
        
        if not seasons_count:
            print(f"[Nove] No seasons found for: {media_item.name}")
            return None
    
        seasons = []
        for s in scrape_serie.seasons_manager.seasons:
            season_num = s.number
            season_name = getattr(s, 'name', None)
            
            episodes_raw = scrape_serie.getEpisodeSeasons(s.number)
            episodes = []
            
            for idx, ep in enumerate(episodes_raw or [], 1):
                episode = Episode(
                    number=getattr(ep, "number", idx),
                    name=getattr(ep, 'name', f"Episodio {idx}"),
                    id=getattr(ep, 'id', idx)
                )
                episodes.append(episode)
            
            season = Season(number=season_num, episodes=episodes, name=season_name)
            seasons.append(season)
            print(f"[Nove] Season {season_num} ({season_name or f'Season {season_num}'}): {len(episodes)} episodes")
        
        return seasons if seasons else None
    
    def start_download(self, media_item: MediaItem, season: Optional[str] = None, episodes: Optional[str] = None) -> bool:
        """
        Start downloading from Nove.
        
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