# 10.12.23

import sys


# External libraries
import httpx


# Internal utilities
from StreamingCommunity.Util.console import console
from StreamingCommunity.Util._jsonConfig import config_manager
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.table import TVShowManager
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Util import search_domain
from StreamingCommunity.Api.Template.Class.SearchType import MediaManager



# Variable
media_search_manager = MediaManager()
table_show_manager = TVShowManager()
max_timeout = config_manager.get_int("REQUESTS", "timeout")
disable_searchDomain = config_manager.get_bool("DEFAULT", "disable_searchDomain")


def title_search(title_search: str) -> int:
    """
    Search for titles based on a search query.
      
    Parameters:
        - title_search (str): The title to search for.

    Returns:
        int: The number of titles found.
    """
    domain_to_use = site_constant

    if not disable_searchDomain:
        domain_to_use, base_url = search_domain(site_constant.SITE_NAME, site_constant.FULL_URL)

    if domain_to_use is None or base_url is None:
        console.print("[bold red]❌ Error: Unable to determine valid domain or base URL.[/bold red]")
        console.print("[yellow]The service might be temporarily unavailable or the domain may have changed.[/yellow]")
        sys.exit(1)

    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()

    media_search_manager.clear()
    table_show_manager.clear()

    search_url = f"{site_constant.FULL_URL}/api/search?q={title_search}"
    console.print(f"[cyan]Search url: [yellow]{search_url}")

    try:
        response = httpx.get(
            url=search_url, 
            headers={'user-agent': get_userAgent()}, 
            timeout=max_timeout,
            verify=site_constant.VERIFY,
            follow_redirects=True
        )
        response.raise_for_status()

    except Exception as e:
        console.print(f"Site: {site_constant.SITE_NAME}, request search error: {e}")

    # Prepara le scelte per l'utente
    if site_constant.TELEGRAM_BOT:
        choices = []
          
    for i, dict_title in enumerate(response.json()['data']):
        try:
            media_search_manager.add_media({
                'id': dict_title.get('id'),
                'slug': dict_title.get('slug'),
                'name': dict_title.get('name'),
                'type': dict_title.get('type'),
                'date': dict_title.get('last_air_date'),
                'score': dict_title.get('score')
            })

            if site_constant.TELEGRAM_BOT:
                choice_text = f"{i} - {dict_title.get('name')} ({dict_title.get('type')}) - {dict_title.get('last_air_date')}"
                choices.append(choice_text)
            
        except Exception as e:
            print(f"Error parsing a film entry: {e}")
	
    if site_constant.TELEGRAM_BOT:
        if choices:
            bot.send_message(f"Lista dei risultati:", choices)
          
    # Return the number of titles found
    return media_search_manager.get_length()