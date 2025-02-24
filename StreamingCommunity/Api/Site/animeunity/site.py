# 10.12.23

import sys
import logging


# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.console import console
from StreamingCommunity.Util._jsonConfig import config_manager
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


def get_token(site_name: str, domain: str) -> dict:
    """
    Function to retrieve session tokens from a specified website.

    Parameters:
        - site_name (str): The name of the site.
        - domain (str): The domain of the site.

    Returns:
        - dict: A dictionary containing session tokens. The keys are 'XSRF_TOKEN', 'animeunity_session', and 'csrf_token'.
    """

    # Send a GET request to the specified URL composed of the site name and domain
    response = httpx.get(
        url=site_constant.FULL_URL,
        timeout=max_timeout
    )
    response.raise_for_status()

    # Initialize variables to store CSRF token
    find_csrf_token = None
    
    # Parse the HTML response using BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Loop through all meta tags in the HTML response
    for html_meta in soup.find_all("meta"):

        # Check if the meta tag has a 'name' attribute equal to "csrf-token"
        if html_meta.get('name') == "csrf-token":

            # If found, retrieve the content of the meta tag, which is the CSRF token
            find_csrf_token = html_meta.get('content')

    logging.info(f"Extract: ('animeunity_session': {response.cookies['animeunity_session']}, 'csrf_token': {find_csrf_token})")
    return {
        'animeunity_session': response.cookies['animeunity_session'],
        'csrf_token': find_csrf_token
    }


def get_real_title(record):
    """
    Get the real title from a record.

    This function takes a record, which is assumed to be a dictionary representing a row of JSON data.
    It looks for a title in the record, prioritizing English over Italian titles if available.
    
    Parameters:
        - record (dict): A dictionary representing a row of JSON data.
    
    Returns:
        - str: The title found in the record. If no title is found, returns None.
    """

    if record['title'] is not None:
        return record['title']
    
    elif record['title_eng'] is not None:
        return record['title_eng']
    
    else:
        return record['title_it']


def title_search(title: str) -> int:
    """
    Function to perform an anime search using a provided title.

    Parameters:
        - title_search (str): The title to search for.

    Returns:
        - int: A number containing the length of media search manager.
    """
    if site_constant.TELEGRAM_BOT:  
        bot = get_bot_instance()
    
    media_search_manager.clear()
    table_show_manager.clear()

    # Get token and session value from configuration
    domain_to_use = site_constant.DOMAIN_NOW
    
    if not disable_searchDomain:
        domain_to_use, base_url = search_domain(site_constant.SITE_NAME, site_constant.FULL_URL)

    if domain_to_use is None or base_url is None:
        console.print("[bold red]❌ Error: Unable to determine valid domain or base URL.[/bold red]")
        console.print("[yellow]The service might be temporarily unavailable or the domain may have changed.[/yellow]")
        sys.exit(1)
    
    data = get_token(site_constant.SITE_NAME, domain_to_use)

    # Prepare cookies to be used in the request
    cookies = {
        'animeunity_session': data.get('animeunity_session')
    }

    # Prepare headers for the request
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json;charset=UTF-8',
        'x-csrf-token': data.get('csrf_token')
    }

    # Prepare JSON data to be sent in the request
    json_data =  {
        'title': title
    }

    # Send a POST request to the API endpoint for live search
    try:
        response = httpx.post(
            url=f'{site_constant.FULL_URL}/livesearch', 
            cookies=cookies, 
            headers=headers, 
            json=json_data,
            timeout=max_timeout,
            verify=site_constant.VERIFY
        )
        response.raise_for_status()

    except Exception as e:
        console.print(f"Site: {site_constant.SITE_NAME}, request search error: {e}")

    # Inizializza la lista delle scelte
    if site_constant.TELEGRAM_BOT:
        choices = []

    for dict_title in response.json()['records']:
        try:

            # Rename keys for consistency
            dict_title['name'] = get_real_title(dict_title)

            media_search_manager.add_media({
                'id': dict_title.get('id'),
                'slug': dict_title.get('slug'),
                'name': dict_title.get('name'),
                'type': dict_title.get('type'),
                'score': dict_title.get('score'),
                'episodes_count': dict_title.get('episodes_count')
            })

            if site_constant.TELEGRAM_BOT:
                # Crea una stringa formattata per ogni scelta con numero
                choice_text = f"{len(choices)} - {dict_title.get('name')} ({dict_title.get('type')}) - Episodi: {dict_title.get('episodes_count')}"
                choices.append(choice_text)

        except Exception as e:
            print(f"Error parsing a film entry: {e}")

    if site_constant.TELEGRAM_BOT:
        if choices:
            bot.send_message(f"Lista dei risultati:", choices)

    # Return the length of media search manager
    return media_search_manager.get_length()