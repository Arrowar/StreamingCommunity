# 03.07.24

# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util._jsonConfig import config_manager
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Util.table import TVShowManager


# Logic class
from StreamingCommunity.Api.Template.Util import search_domain
from StreamingCommunity.Api.Template.Class.SearchType import MediaManager


# Variable
from .costant import SITE_NAME, DOMAIN_NOW
media_search_manager = MediaManager()
table_show_manager = TVShowManager()
max_timeout = config_manager.get_int("REQUESTS", "timeout")
disable_searchDomain = config_manager.get_bool("DEFAULT", "disable_searchDomain")


def title_search(word_to_search: str) -> int:
    """
    Search for titles based on a search query.

    Parameters:
        - title_search (str): The title to search for.

    Returns:
        - int: The number of titles found.
    """
    media_search_manager.clear()
    table_show_manager.clear()

    # Find new domain if prev dont work
    domain_to_use = DOMAIN_NOW
    
    if not disable_searchDomain:
        domain_to_use, base_url = search_domain(SITE_NAME, f"https://{SITE_NAME}.{DOMAIN_NOW}")

    response = httpx.get(
        url=f"https://{SITE_NAME}.{domain_to_use}/?s={word_to_search}",
        headers={'user-agent': get_headers()},
        timeout=max_timeout
    )
    response.raise_for_status()

    # Create soup and find table
    soup = BeautifulSoup(response.text, "html.parser")

    for div in soup.find_all("div", class_ = "card-content"):
        try:

            url = div.find("h3").find("a").get("href")
            title = div.find("h3").find("a").get_text(strip=True)
            desc = div.find("p").find("strong").text

            title_info = {
                'name': title,
                'desc': desc,
                'url': url
            }

            media_search_manager.add_media(title_info)

        except Exception as e:
            print(f"Error parsing a film entry: {e}")

    # Return the number of titles found
    return media_search_manager.get_length()