# 06-06-25 By @FrancescoGrazioso -> "https://github.com/FrancescoGrazioso"


import importlib
from typing import List, Optional


# Internal utilities
from .base import BaseStreamingAPI, MediaItem, Season, Episode


# External utilities
from StreamingCommunity.utils import config_manager
from StreamingCommunity.services._base.loader import get_folder_name
from StreamingCommunity.services.streamingcommunity.util.ScrapeSerie import GetSerieInfo


class StreamingCommunityAPI(BaseStreamingAPI):
    def __init__(self):
        super().__init__()
        self.site_name = "streamingcommunity"
        self._load_config()
        self._search_fn = None
    
    def _load_config(self):
        """Load site configuration."""
        self.base_url = config_manager.domain.get("streamingcommunity", "full_url")
    
    def _get_search_fn(self):
        """Lazy load the search function."""
        if self._search_fn is None:
            module = importlib.import_module(f"StreamingCommunity.{get_folder_name()}.streamingcommunity")
            self._search_fn = getattr(module, "search")
        return self._search_fn
    
    def search(self, query: str) -> List[MediaItem]:
        """
        Search for content on StreamingCommunity.
        
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
                    id=item_dict.get('id'),
                    name=item_dict.get('name'),
                    slug=item_dict.get('slug', ''),
                    type=item_dict.get('type'),
                    url=item_dict.get('url'),
                    poster=item_dict.get('image'),
                    year=item_dict.get('year'),
                    provider_language=item_dict.get('provider_language'),
                    raw_data=item_dict
                )
                results.append(media_item)
        
        return results

    def get_series_metadata(self, media_item: MediaItem) -> Optional[List[Season]]:
        """
        Get seasons and episodes for a StreamingCommunity series.
        
        Args:
            media_item: MediaItem to get metadata for
            
        Returns:
            List of Season objects, or None if not a series
        """
        # Check if it's a movie
        if media_item.is_movie:
            return None
        
        scraper = GetSerieInfo(
            url=f"{self.base_url}{media_item.provider_language}",
            media_id=media_item.id,
            series_name=media_item.slug,
            year=media_item.year,
            provider_language=media_item.provider_language
        )
        
        seasons_count = scraper.getNumberSeason()
        if not seasons_count:
            return None
        
        seasons = []
        for season_num in range(1, seasons_count + 1):
            episodes_raw = scraper.getEpisodeSeasons(season_num)
            episodes = []
            
            for idx, ep in enumerate(episodes_raw or [], 1):
                episode = Episode(
                    number=idx,
                    name=getattr(ep, 'name', f"Episodio {idx}"),
                    id=getattr(ep, 'id', idx)
                )
                episodes.append(episode)
            
            season = Season(number=season_num, episodes=episodes)
            seasons.append(season)
        
        return seasons if seasons else None

    def start_download(self, media_item: MediaItem, season: Optional[str] = None, episodes: Optional[str] = None) -> bool:
        """
        Start downloading from StreamingCommunity.
        
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