# 06-06-25 By @FrancescoGrazioso -> "https://github.com/FrancescoGrazioso"


from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Entries:
    """Standardized media item representation."""
    name: str
    type: str  # 'film', 'series', 'ova', etc.
    slug: str = None
    id: Any = None
    path_id: Optional[str] = None
    url: Optional[str] = None
    poster: Optional[str] = None
    year: Optional[int] = None
    provider_language: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    @property
    def is_movie(self) -> bool:
        return self.type.lower() in ['film', 'movie', 'ova']
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'path_id': self.path_id,
            'type': self.type,
            'url': self.url,
            'poster': self.poster,
            'year': self.year,
            'raw_data': self.raw_data,
            'is_movie': self.is_movie,
            'provider_language': self.provider_language
        }


@dataclass
class Episode:
    """Episode information."""
    number: int
    name: str
    id: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'number': self.number,
            'name': self.name,
            'id': self.id
        }


@dataclass
class Season:
    """Season information."""
    number: int
    episodes: List[Episode]
    name: Optional[str] = None
    
    @property
    def episode_count(self) -> int:
        return len(self.episodes)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'number': self.number,
            'name': self.name,
            'episodes': [ep.to_dict() for ep in self.episodes],
            'episode_count': self.episode_count
        }


class BaseStreamingAPI(ABC):
    _scraper_cache: Dict[str, Any] = {}  # Global cache to persist scrapers across instances

    def __init__(self):
        self.site_name: str = ""
        self.base_url: str = ""

    def _get_cache_key(self, media_item: Entries) -> str:
        """Generate a unique key for the scraper cache."""
        return f"{self.site_name}_{media_item.url or media_item.path_id or media_item.id or media_item.slug}"

    def get_cached_scraper(self, media_item: Entries) -> Optional[Any]:
        """Retrieve a cached scraper instance from the global cache."""
        key = self._get_cache_key(media_item)
        return self._scraper_cache.get(key)

    def set_cached_scraper(self, media_item: Entries, scraper: Any):
        """Store a scraper instance in the global cache."""
        key = self._get_cache_key(media_item)
        self._scraper_cache[key] = scraper

    @abstractmethod
    def search(self, query: str) -> List[Entries]:
        """
        Search for content on the streaming site.
        
        Args:
            query: Search term
            
        Returns:
            List of Entries objects
        """
        pass
    
    @abstractmethod
    def get_series_metadata(self, media_item: Entries) -> Optional[List[Season]]:
        """
        Get seasons and episodes for a series.
        
        Args:
            media_item: Entries to get metadata for
            
        Returns:
            List of Season objects, or None if not a series
        """
        pass
    
    @abstractmethod
    def start_download(self, media_item: Entries, season: Optional[str] = None, episodes: Optional[str] = None) -> bool:
        """
        Start downloading content.
        
        Args:
            media_item: Entries to download
            season: Season number (for series)
            episodes: Episode selection (e.g., "1-5" or "1,3,5" or "*" for all)
            
        Returns:
            True if download started successfully
        """
        pass
    
    def ensure_complete_item(self, partial_item: Dict[str, Any]) -> Entries:
        """
        Ensure a media item has all required fields by searching the database.
        
        Args:
            partial_item: Dictionary with partial item data
            
        Returns:
            Complete Entries object
        """
        # If already complete, convert to Entries
        if partial_item.get('path_id') or (partial_item.get('id') and (partial_item.get('slug') or partial_item.get('url'))):
            return self._dict_to_entries(partial_item)
        
        # Try to find in database
        query = (partial_item.get('name') or partial_item.get('slug') or partial_item.get('display_title'))
        
        if query:
            results = self.search(query)
            if results:
                wanted_slug = partial_item.get('slug')
                if wanted_slug:
                    for item in results:
                        if item.slug == wanted_slug:
                            return item
                        
                return results[0]
        
        # Fallback: return partial item
        return self._dict_to_entries(partial_item)
    
    def _dict_to_entries(self, data: Dict[str, Any]) -> Entries:
        """Convert dictionary to Entries."""
        return Entries(
            id=data.get('id'),
            name=data.get('name') or 'Unknown',
            slug=data.get('slug') or '',
            path_id=data.get('path_id'),
            type=data.get('type') or data.get('media_type') or 'unknown',
            url=data.get('url'),
            poster=data.get('poster') or data.get('poster_url') or data.get('image'),
            year=data.get('year'),
            provider_language=data.get('provider_language'),
            raw_data=data.get('raw_data', data)
        )