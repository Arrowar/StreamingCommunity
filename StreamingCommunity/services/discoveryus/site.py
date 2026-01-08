# 22.12.25

# External libraries
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils.http_client import create_client
from StreamingCommunity.services._base import site_constants, MediaManager
from StreamingCommunity.utils import TVShowManager


# Logic
from .util.get_license import get_api


# Variables
console = Console()
media_search_manager = MediaManager()
table_show_manager = TVShowManager()


def title_search(query: str) -> int:
    """
    Search for titles on Discovery+
    
    Parameters:
        query (str): Search query
        
    Returns:
        int: Number of results found
    """
    media_search_manager.clear()
    table_show_manager.clear()
    
    api = get_api()
    search_url = 'https://us1-prod-direct.go.discovery.com/cms/routes/search/result'
    console.print(f"[cyan]Search url: [yellow]{search_url}")
    
    params = {
        'include': 'default',
        'decorators': 'viewingHistory,isFavorite,playbackAllowed',
        'contentFilter[query]': query
    }
    
    try:
        response = create_client(headers=api.get_request_headers()).get(
            search_url,
            params=params,
            cookies=api.get_cookies()
        )
        response.raise_for_status()
        
    except Exception as e:
        console.print(f"[red]Site: {site_constants.SITE_NAME}, request search error: {e}")
        return 0
    
    # Parse response
    data = response.json()
    for element in data.get('included', []):
        element_type = element.get('type')
        
        # Handle both shows and movies
        if element_type in ['show', 'movie']:
            attributes = element.get('attributes', {})
            
            if 'name' in attributes:
                if element_type == 'show':
                    date = attributes.get('newestEpisodeDate', '').split("T")[0]
                else:
                    date = attributes.get('airDate', '').split("T")[0]
                
                combined_id = f"{element.get('id')}|{attributes.get('alternateId')}"
                media_search_manager.add_media({
                    'id': combined_id,
                    'name': attributes.get('name', 'No Title'),
                    'type': 'tv' if element_type == 'show' else 'movie',
                    'image': None,
                    'date': date
                })
    
    return media_search_manager.get_length()