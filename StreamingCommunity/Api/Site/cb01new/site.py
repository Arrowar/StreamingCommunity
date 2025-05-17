# 03.07.24

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

    search_url = f"{site_constant.FULL_URL}/?s={query}"
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
        console.print(f"Site: {site_constant.SITE_NAME}, request search error: {e}")
        return 0

    # Create soup and find table
    soup = BeautifulSoup(response.text, "html.parser")

    for card in soup.find_all("div", class_=["card", "mp-post", "horizontal"]):
        try:
            title_tag = card.find("h3", class_="card-title").find("a")
            url = title_tag.get("href")
            title = title_tag.get_text(strip=True)

            title_info = {
                'name': title,
                'url': url,
                'type': 'film'
            }

            media_search_manager.add_media(title_info)

        except Exception as e:
            print(f"Error parsing a film entry: {e}")

    # Return the number of titles found
    return media_search_manager.get_length()