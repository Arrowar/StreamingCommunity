# 26.11.2025


# External libraries
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils.http_client import create_client, get_userAgent
from StreamingCommunity.utils import TVShowManager
from StreamingCommunity.services._base import site_constants, MediaManager


# Logic
from .util.get_license import get_bearer_token


# Variable
console = Console()
media_search_manager = MediaManager()
table_show_manager = TVShowManager()


def title_search(query: str) -> int:
    """
    Search for titles based on a search query.
      
    Parameters:
        - query (str): The query to search for.

    Returns:
        int: The number of titles found.
    """
    media_search_manager.clear()
    table_show_manager.clear()

    search_url = f"https://service-media-search.clusters.pluto.tv/v1/search?q={query}&limit=10"
    console.print(f"[cyan]Search url: [yellow]{search_url}")

    try:
        response = create_client(headers={'user-agent': get_userAgent(), 'Authorization': f"Bearer {get_bearer_token()}"}).get(search_url)
        response.raise_for_status()

    except Exception as e:
        console.print(f"[red]Site: {site_constants.SITE_NAME}, request search error: {e}")
        return 0

    # Collect json data
    try:
        data = response.json().get('data')
    except Exception as e:
        console.log(f"Error parsing JSON response: {e}")
        return 0

    for dict_title in data:
        try:
            if dict_title.get('type') == 'channel':
                continue

            define_type = 'tv' if dict_title.get('type') == 'series' else dict_title.get('type')
            
            media_search_manager.add_media({
                'id': dict_title.get('id'),
                'name': dict_title.get('name'),
                'type': define_type,
                'image': None,
                'url': f"https://service-vod.clusters.pluto.tv/v4/vod/{dict_title.get('type')}/{dict_title.get('id')}"
            })
            
        except Exception as e:
            print(f"Error parsing a film entry: {e}")
	
    # Return the number of titles found
    return media_search_manager.get_length()