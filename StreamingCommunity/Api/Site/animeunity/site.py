# 10.12.23

import logging


# External libraries
import httpx
from bs4 import BeautifulSoup
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.table import TVShowManager
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaManager


# Variable
console = Console()
media_search_manager = MediaManager()
table_show_manager = TVShowManager()
max_timeout = config_manager.get_int("REQUESTS", "timeout")


def get_token() -> dict:
    """
    Function to retrieve session tokens from a specified website.

    Parameters:
        - site_name (str): The name of the site.
        - domain (str): The domain of the site.

    Returns:
        - dict: A dictionary containing session tokens. The keys are 'XSRF_TOKEN', 'animeunity_session', and 'csrf_token'.
    """
    response = httpx.get(
        url=site_constant.FULL_URL,
        timeout=max_timeout
    )
    response.raise_for_status()

    # Initialize variables to store CSRF token
    find_csrf_token = None
    soup = BeautifulSoup(response.text, "html.parser")
    
    for html_meta in soup.find_all("meta"):
        if html_meta.get('name') == "csrf-token":
            find_csrf_token = html_meta.get('content')

    return {
        'animeunity_session': response.cookies['animeunity_session'],
        'csrf_token': find_csrf_token
    }


def get_real_title(record):
    """
    Get the real title from a record.
    
    Parameters:
        - record (dict): A dictionary representing a row of JSON data.
    
    Returns:
        - str: The title found in the record. If no title is found, returns None.
    """
    if record['title_eng'] is not None:
        return record['title_eng']
    elif record['title'] is not None:
        return record['title']
    else:
        return record['title_it']


def title_search(query: str) -> int:
    """
    Function to perform an anime search using both APIs and combine results.

    Parameters:
        - query (str): The query to search for.

    Returns:
        - int: A number containing the length of media search manager.
    """
    if site_constant.TELEGRAM_BOT:  
        bot = get_bot_instance()
    
    media_search_manager.clear()
    table_show_manager.clear()
    seen_titles = set()
    choices = [] if site_constant.TELEGRAM_BOT else None

    # Create parameter for request
    data = get_token()
    cookies = {
        'animeunity_session': data.get('animeunity_session')
    }
    headers = {
        'user-agent': get_userAgent(),
        'x-csrf-token': data.get('csrf_token')
    }

    # First API call - livesearch
    try:
        response1 = httpx.post(
            f'{site_constant.FULL_URL}/livesearch',
            cookies=cookies,
            headers=headers,
            json={'title': query},
            timeout=max_timeout
        )
        
        response1.raise_for_status()
        process_results(response1.json()['records'], seen_titles, media_search_manager, choices)

    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request search error: {e}")
        return 0

    # Second API call - archivio
    try:
        json_data = {
            'title': query,
            'type': False,
            'year': False,
            'order': 'Lista A-Z',
            'status': False,
            'genres': False,
            'offset': 0,
            'dubbed': False,
            'season': False
        }

        response2 = httpx.post(
            f'{site_constant.FULL_URL}/archivio/get-animes',
            cookies=cookies,
            headers=headers,
            json=json_data,
            timeout=max_timeout
        )

        response2.raise_for_status()
        process_results(response2.json()['records'], seen_titles, media_search_manager, choices)

    except Exception as e:
        console.print(f"Site: {site_constant.SITE_NAME}, archivio search error: {e}")

    if site_constant.TELEGRAM_BOT and choices and len(choices) > 0:
        bot.send_message(f"Lista dei risultati:", choices)
    
    result_count = media_search_manager.get_length()
    if result_count == 0:
        console.print(f"Nothing matching was found for: {query}")
    
    return result_count

def process_results(records: list, seen_titles: set, media_manager: MediaManager, choices: list = None) -> None:
    """Helper function to process search results and add unique entries."""
    for dict_title in records:
        try:
            title_id = dict_title.get('id')
            if title_id in seen_titles:
                continue
                
            seen_titles.add(title_id)
            dict_title['name'] = get_real_title(dict_title)

            media_manager.add_media({
                'id': title_id,
                'slug': dict_title.get('slug'),
                'name': dict_title.get('name'),
                'type': dict_title.get('type'),
                'status': dict_title.get('status'),
                'episodes_count': dict_title.get('episodes_count'),
                'image': dict_title.get('imageurl')
            })

            if choices is not None:
                choice_text = f"{len(choices)} - {dict_title.get('name')} ({dict_title.get('type')}) - Episodi: {dict_title.get('episodes_count')}"
                choices.append(choice_text)

        except Exception as e:
            print(f"Error parsing a title entry: {e}")
