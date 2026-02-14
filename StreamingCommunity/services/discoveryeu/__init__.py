# 22.12.25

# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import TVShowManager
from StreamingCommunity.utils.http_client import create_client, check_region_availability
from StreamingCommunity.services._base import site_constants, EntriesManager, Entries
from StreamingCommunity.services._base.site_search_manager import base_process_search_result, base_search


# Logic
from .client import get_api
from .downloader import download_series


# Variables
indice = 14
_useFor = "Film_&_Serie"
_region = ["IT"]
_drm = ["widevine", "playready", "fairplay"]
msg = Prompt()
console = Console()
entries_manager = EntriesManager()
table_show_manager = TVShowManager()


def determine_type(attributes: dict)-> str:
    """
    Determines the item type
    
    Parameters:
        attributes (dict): Dictionary with item info

    Returns:
        str: Type of the item
    """
    episode_count = attributes.get('episodeCount', 0)
    video_count = attributes.get('videoCount', 0)
    if episode_count == 0 and  video_count > 1000:
        return 'channel'
    elif episode_count > 0:
        return 'show'
    elif video_count == 1 and episode_count == 0:
        return 'movie'
    else:
        return "unknown"

def title_search(query: str) -> int:
    """
    Search for titles on Discovery+
    
    Parameters:
        query (str): Search query
        
    Returns:
        int: Number of results found
    """
    entries_manager.clear()
    table_show_manager.clear()

    if not check_region_availability(_region, site_constants.SITE_NAME):
        return 0
    
    api = get_api()
    search_url = 'https://eu1-prod-direct.discoveryplus.com/cms/routes/search/result'
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
        attributes = element.get('attributes', {})
        type_element = determine_type(attributes)
     
        if element_type != type_element:
            continue
            
        # Handle both shows and movies
        if element_type in ['show', 'movie']:
            if 'name' in attributes:
                if element_type == 'show':
                    date = attributes.get('newestEpisodeDate', '').split("T")[0]
                else:
                    date = attributes.get('airDate', '').split("T")[0]
                
                combined_id = f"{element.get('id')}|{attributes.get('alternateId')}"
                entries_manager.add(Entries(
                    id=combined_id,
                    name=attributes.get('name', 'No Title'),
                    type='tv' if element_type == 'show' else 'movie',
                    image=None,
                    year=date
                ))
                
    return len(entries_manager)



# WRAPPING FUNCTIONS
def process_search_result(select_title, selections=None, scrape_serie=None):
    """
    Wrapper for the generalized process_search_result function.
    """
    return base_process_search_result(
        select_title=select_title,
        download_film_func=None,
        download_series_func=download_series,
        media_search_manager=entries_manager,
        table_show_manager=table_show_manager,
        selections=selections,
        scrape_serie=scrape_serie
    )

def search(string_to_search: str = None, get_onlyDatabase: bool = False, direct_item: dict = None, selections: dict = None, scrape_serie=None):
    """
    Wrapper for the generalized search function.
    """
    return base_search(
        title_search_func=title_search,
        process_result_func=process_search_result,
        media_search_manager=entries_manager,
        table_show_manager=table_show_manager,
        site_name=site_constants.SITE_NAME,
        string_to_search=string_to_search,
        get_onlyDatabase=get_onlyDatabase,
        direct_item=direct_item,
        selections=selections,
        scrape_serie=scrape_serie
    )