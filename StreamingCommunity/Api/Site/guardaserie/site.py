# 09.06.24

# External libraries
import httpx
from bs4 import BeautifulSoup
from rich.console import Console

# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.table import TVShowManager


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaManager


# Variable
console = Console()
media_search_manager = MediaManager()
table_show_manager = TVShowManager()
max_timeout = config_manager.get_int("REQUESTS", "timeout")



def title_search(query: str) -> int:
    """
    Search for titles based on a search query.

    Parameters:
        - query (str): The query to search for.

    Returns:
        - int: The number of titles found.
    """
    media_search_manager.clear()
    table_show_manager.clear()

    search_url = f"{site_constant.FULL_URL}/?story={query}&do=search&subaction=search"
    console.print(f"[cyan]Search url: [yellow]{search_url}")

    try:
        response = httpx.get(
            search_url, 
            headers={'user-agent': get_userAgent()}, 
            timeout=max_timeout, 
            follow_redirects=True, 
            verify=False
        )
        response.raise_for_status()
    
    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request search error: {e}")
        return 0

    # Create soup and find table
    soup = BeautifulSoup(response.text, "html.parser")

    for serie_div in soup.find_all('div', class_='entry'):
        try:
            serie_info = {
                'name': serie_div.find('a').get("title").replace("streaming guardaserie", ""),
                'url': serie_div.find('a').get("href"),
                'type': 'tv',
                'image': f"{site_constant.FULL_URL}/{serie_div.find('img').get('src')}",
            }
            media_search_manager.add_media(serie_info)

        except Exception as e:
            print(f"Error parsing a film entry: {e}")

    # Return the number of titles found
    return media_search_manager.get_length()