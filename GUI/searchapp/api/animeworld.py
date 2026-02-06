# 27.01.26


import importlib
from typing import List, Optional


# Internal utilities
from .base import BaseStreamingAPI, MediaItem, Season, Episode


# External utilities
from StreamingCommunity.utils import config_manager
from StreamingCommunity.services._base.site_loader import get_folder_name
from StreamingCommunity.services.animeworld.scrapper import ScrapSerie


class AnimeWorldAPI(BaseStreamingAPI):
    def __init__(self):
        super().__init__()
        self.site_name = "animeworld"
        self._load_config()
        self._search_fn = None
        self._scrapper = None
    
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
        Search for anime content on AnimeWorld.
        
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
                    type=item_dict.get('type', 'TV'),
                    url=item_dict.get('url'),
                    poster=item_dict.get('image'),
                    year=item_dict.get('year'),
                    raw_data=item_dict
                )
                results.append(media_item)
        
        return results
    
    def get_series_metadata(self, media_item: MediaItem) -> Optional[List[Season]]:
        """
        Get episodes for an AnimeWorld series.
        
        Args:
            media_item: MediaItem to get metadata for
            
        Returns:
            List with a single Season containing all episodes, or None if it's a movie
        """
        if media_item.type == 'Movie':
            return None
        
        scrape_serie = ScrapSerie(media_item.url, self.base_url)
        episodes_data = scrape_serie.get_episodes()
        
        if not episodes_data:
            print(f"[AnimeWorld] No episodes found for: {media_item.name}")
            return None
        
        # Create episodes list
        episodes = []
        for idx, ep_data in enumerate(episodes_data, 1):
            episode = Episode(
                number=idx,
                name=getattr(ep_data, 'name', f"Episode {idx}"),
                id=getattr(ep_data, 'id', idx)
            )
            episodes.append(episode)
        
        season = Season(number=1, episodes=episodes, name="Episodes")
        print(f"[AnimeWorld] Found {len(episodes)} episodes for: {media_item.name}")
        
        return [season]
    
    def start_download(self, media_item: MediaItem, season: Optional[str] = None, episodes: Optional[str] = None) -> bool:
        """
        Start downloading from AnimeWorld.
        
        Args:
            media_item: MediaItem to download
            season: Season number (typically not used for anime, defaults to None)
            episodes: Episode selection
            
        Returns:
            True if download started successfully
        """
        search_fn = self._get_search_fn()
        
        # Prepare direct_item from MediaItem
        direct_item = media_item.raw_data or media_item.to_dict()
        
        # Prepare selections
        selections = None
        if episodes:
            selections = {
                'episode': episodes
            }
        
        # Execute download
        search_fn(direct_item=direct_item, selections=selections)
        return True