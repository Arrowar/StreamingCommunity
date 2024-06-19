# 10.12.23

import logging


# External libraries
import httpx
from bs4 import BeautifulSoup
from unidecode import unidecode


# Internal utilities
from Src.Util.table import TVShowManager
from ..Template import search_domain, get_select_title


# Logic class
from .Core.Class.SearchType import MediaManager


# Variable
from .costant import SITE_NAME
media_search_manager = MediaManager()
table_show_manager = TVShowManager()



def get_token(site_name: str, domain: str) -> dict:
    """
    Function to retrieve session tokens from a specified website.

    Args:
        - site_name (str): The name of the site.
        - domain (str): The domain of the site.

    Returns:
        - dict: A dictionary containing session tokens. The keys are 'XSRF_TOKEN', 'animeunity_session', and 'csrf_token'.
    """

    # Send a GET request to the specified URL composed of the site name and domain
    response = httpx.get(f"https://www.{site_name}.{domain}")
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
    
    Args:
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

    Args:
        - title_search (str): The title to search for.

    Returns:
        - int: A number containing the length of media search manager.
    """

    # Get token and session value from configuration
    domain_to_use, _ = search_domain(SITE_NAME, '<meta name="author" content="AnimeUnity Staff">', f"https://www.{SITE_NAME}")
    data = get_token(SITE_NAME, domain_to_use)

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
    json_data = {
        'title': unidecode(title)  # Use the provided title for the search
    }

    # Send a POST request to the API endpoint for live search
    response = httpx.post(f'https://www.{SITE_NAME}.{domain_to_use}/livesearch', cookies=cookies, headers=headers, json=json_data)
    response.raise_for_status()

    # Process each record returned in the response
    for record in response.json()['records']:

        # Rename keys for consistency
        record['name'] = get_real_title(record)
        record['last_air_date'] = record.pop('date')  

        # Add the record to media search manager if the name is not None
        media_search_manager.add_media(record)

    # Return the length of media search manager
    return media_search_manager.get_length()



def run_get_select_title():
    """
    Display a selection of titles and prompt the user to choose one.
    """
    return get_select_title(table_show_manager, media_search_manager)