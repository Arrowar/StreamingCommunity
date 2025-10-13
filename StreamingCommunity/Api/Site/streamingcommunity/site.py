# 10.12.23

import json


# External libraries
from bs4 import BeautifulSoup
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.http_client import create_client
from StreamingCommunity.Util.table import TVShowManager
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaManager


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
    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()

    media_search_manager.clear()
    table_show_manager.clear()

    try:
        response = create_client(headers={'user-agent': get_userAgent()}).get(f"{site_constant.FULL_URL}/it")
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        version = json.loads(soup.find('div', {'id': "app"}).get("data-page"))['version']

    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME} version, request error: {e}")
        return 0

    search_url = f"{site_constant.FULL_URL}/it/search?q={query}"
    console.print(f"[cyan]Search url: [yellow]{search_url}")

    try:
        response = create_client(headers={'user-agent': get_userAgent(), 'x-inertia': 'true', 'x-inertia-version': version}).get(search_url)
        response.raise_for_status()

    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request search error: {e}")
        if site_constant.TELEGRAM_BOT:
            bot.send_message(f"ERRORE\n\nErrore nella richiesta di ricerca:\n\n{e}", None)
        return 0

    # Prepara le scelte per l'utente
    if site_constant.TELEGRAM_BOT:
        choices = []

    # Collect json data
    try:
        data = response.json().get('props').get('titles')
    except Exception as e:
        console.log(f"Error parsing JSON response: {e}")
        return 0

    for i, dict_title in enumerate(data):
        try:
            media_search_manager.add_media({
                'id': dict_title.get('id'),
                'slug': dict_title.get('slug'),
                'name': dict_title.get('name'),
                'type': dict_title.get('type'),
                'date': dict_title.get('last_air_date'),
                'image': f"{site_constant.FULL_URL.replace('stream', 'cdn.stream')}/images/{dict_title.get('images')[0].get('filename')}"
            })

            if site_constant.TELEGRAM_BOT:
                choice_text = f"{i} - {dict_title.get('name')} ({dict_title.get('type')}) - {dict_title.get('last_air_date')}"
                choices.append(choice_text)
            
        except Exception as e:
            print(f"Error parsing a film entry: {e}")
            if site_constant.TELEGRAM_BOT:
                bot.send_message(f"ERRORE\n\nErrore nell'analisi del film:\n\n{e}", None)
	
    if site_constant.TELEGRAM_BOT:
        if choices:
            bot.send_message("Lista dei risultati:", choices)
          
    # Return the number of titles found
    return media_search_manager.get_length()
