# 10.12.23

import json
import logging
import secrets


# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.console import console
from StreamingCommunity.Util._jsonConfig import config_manager
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Util.table import TVShowManager
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance


# Logic class
from StreamingCommunity.Api.Template.Util import search_domain
from StreamingCommunity.Api.Template.Class.SearchType import MediaManager


# Config
from .costant import SITE_NAME, DOMAIN_NOW, TELEGRAM_BOT


# Variable
media_search_manager = MediaManager()
table_show_manager = TVShowManager()
max_timeout = config_manager.get_int("REQUESTS", "timeout")
disable_searchDomain = config_manager.get_bool("DEFAULT", "disable_searchDomain")


def get_version(domain: str):
    """
    Extracts the version from the HTML text of a webpage.

    Parameters:
        - domain (str): The domain of the site.

    Returns:
        str: The version extracted from the webpage.
    """
    try:
        response = httpx.get(
            url=f"https://{SITE_NAME}.{domain}/", 
            headers={'User-Agent': get_headers()}, 
            timeout=max_timeout
        )
        response.raise_for_status()

        # Parse request to site
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract version
        version = json.loads(soup.find("div", {"id": "app"}).get("data-page"))['version']
        #console.print(f"[cyan]Get version [white]=> [red]{version} \n")

        return version
    
    except Exception as e:
        logging.error(f"Error extracting version: {e}")
        raise


def get_version_and_domain():
    """
    Retrieve the current version and domain of the site.

    This function performs the following steps:
        - Determines the correct domain to use for the site by searching for a specific meta tag.
        - Fetches the content of the site to extract the version information.
    """

    # Find new domain if prev dont work
    domain_to_use = DOMAIN_NOW

    if not disable_searchDomain:
        domain_to_use, base_url = search_domain(SITE_NAME, f"https://{SITE_NAME}.{DOMAIN_NOW}")

    try:
        version = get_version(domain_to_use)
    except:
        #console.print("[green]Auto generate version ...")
        #version = secrets.token_hex(32 // 2)
        version = None
            
    return version, domain_to_use


def title_search(title_search: str, domain: str) -> int:
    """
    Search for titles based on a search query.
      
    Parameters:
        - title_search (str): The title to search for.
        - domain (str): The domain to search on.

    Returns:
        int: The number of titles found.
    """
    if TELEGRAM_BOT:
        bot = get_bot_instance()

    media_search_manager.clear()
    table_show_manager.clear()
    
    try:
        response = httpx.get(
            url=f"https://{SITE_NAME}.{domain}/api/search?q={title_search.replace(' ', '+')}", 
            headers={'user-agent': get_headers()}, 
            timeout=max_timeout
        )
        response.raise_for_status()

    except Exception as e:
        console.print(f"Site: {SITE_NAME}, request search error: {e}")

    # Prepara le scelte per l'utente
    if TELEGRAM_BOT:
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

            if TELEGRAM_BOT:
                choice_text = f"{i} - {dict_title.get('name')} ({dict_title.get('type')}) - {dict_title.get('last_air_date')}"
                choices.append(choice_text)
            
        except Exception as e:
            print(f"Error parsing a film entry: {e}")
	
    if TELEGRAM_BOT:
        if choices:
            bot.send_message(f"Lista dei risultati:", choices)
          
    # Return the number of titles found
    return media_search_manager.get_length()