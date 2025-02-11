# 09.06.24

# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.console import console
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

    # Send request to search for titles
    try:
        response = httpx.get(
            url=f"https://guardaserie.{domain_to_use}/?story={word_to_search}&do=search&subaction=search", 
            headers={'user-agent': get_headers()}, 
            timeout=max_timeout
        )
        response.raise_for_status()
    
    except Exception as e:
        console.print(f"Site: {SITE_NAME}, request search error: {e}")

    # Create soup and find table
    soup = BeautifulSoup(response.text, "html.parser")
    table_content = soup.find('div', class_="mlnew-list")

    for serie_div in table_content.find_all('div', class_='mlnew'):
        try:
            
            title = serie_div.find('div', class_='mlnh-2').find("h2").get_text(strip=True)
            link = serie_div.find('div', class_='mlnh-2').find('a')['href']
            imdb_rating = serie_div.find('span', class_='mlnh-imdb').get_text(strip=True)

            serie_info = {
                'name': title,
                'url': link,
                'score': imdb_rating
            }

            media_search_manager.add_media(serie_info)

        except Exception as e:
            print(f"Error parsing a film entry: {e}")

    # Return the number of titles found
    return media_search_manager.get_length()