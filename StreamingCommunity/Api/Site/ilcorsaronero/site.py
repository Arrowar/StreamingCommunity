# 02.07.24


# Internal utilities
from StreamingCommunity.Util._jsonConfig import config_manager
from StreamingCommunity.Util.table import TVShowManager


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Util import search_domain
from StreamingCommunity.Api.Template.Class.SearchType import MediaManager
from .util.ilCorsarScraper import IlCorsaroNeroScraper


# Variable
media_search_manager = MediaManager()
table_show_manager = TVShowManager()
max_timeout = config_manager.get_int("REQUESTS", "timeout")
disable_searchDomain = config_manager.get_bool("DEFAULT", "disable_searchDomain")


async def title_search(word_to_search: str) -> int:
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
    domain_to_use = site_constant.DOMAIN_NOW
    
    if not disable_searchDomain:
        domain_to_use, base_url = search_domain(site_constant.SITE_NAME, f"https://{site_constant.SITE_NAME}.{site_constant.DOMAIN_NOW}")

    # Create scraper and collect result
    print("\n")
    scraper = IlCorsaroNeroScraper(f"https://{site_constant.SITE_NAME}.{domain_to_use}/", 1)
    results = await scraper.search(word_to_search)

    for i, torrent in enumerate(results):
        try:
            
            media_search_manager.add_media({
                'name': torrent['name'],
                'type': torrent['type'],
                'seed': torrent['seed'],
                'leech': torrent['leech'],
                'size': torrent['size'],
                'date': torrent['date'],
                'url': torrent['url']
            })

        except Exception as e:
            print(f"Error parsing a film entry: {e}")

    # Return the number of titles found
    return media_search_manager.get_length()