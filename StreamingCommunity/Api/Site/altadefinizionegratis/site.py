# 26.05.24

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

# Telegram bot instance
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance
from StreamingCommunity.Util._jsonConfig import config_manager
TELEGRAM_BOT = config_manager.get_bool('DEFAULT', 'telegram_bot')


def title_search(title_search: str) -> int:
    """
    Search for titles based on a search query.

    Parameters:
        - title_search (str): The title to search for.

    Returns:
        int: The number of titles found.
    """
    if TELEGRAM_BOT:  
        bot = get_bot_instance()

    media_search_manager.clear()
    table_show_manager.clear()

    # Find new domain if prev dont work
    domain_to_use = DOMAIN_NOW
    
    if not disable_searchDomain:
        domain_to_use, base_url = search_domain(SITE_NAME, f"https://{SITE_NAME}.{DOMAIN_NOW}")
        
    # Send request to search for title
    client = httpx.Client()

    try:
        response = client.get(
            url=f"https://{SITE_NAME}.{domain_to_use}/?story={title_search.replace(' ', '+')}&do=search&subaction=search&titleonly=3", 
            headers={'User-Agent': get_headers()},
            timeout=max_timeout
        )
        response.raise_for_status()

    except Exception as e:
        console.print(f"Site: {SITE_NAME}, request search error: {e}")
        raise

    # Create soup and find table
    soup = BeautifulSoup(response.text, "html.parser")

    # Inizializza la lista delle scelte
    if TELEGRAM_BOT:
        choices = []

    for row in soup.find_all('div', class_='col-lg-3 col-md-3 col-xs-4'):
        try:
            
            title_element = row.find('h2', class_='titleFilm').find('a')
            title = title_element.get_text(strip=True)
            link = title_element['href']

            imdb_element = row.find('div', class_='imdb-rate')
            imdb_rating = imdb_element.get_text(strip=True).split(":")[-1]

            film_info = {
                'name': title,
                'url': link,
                'score': imdb_rating
            }
            
            media_search_manager.add_media(film_info)

            if TELEGRAM_BOT:
                # Crea una stringa formattata per ogni scelta con numero
                choice_text = f"{len(choices)} - {film_info.get('name')} ({film_info.get('url')}) {film_info.get('score')}"
                choices.append(choice_text)

        except AttributeError as e:
            print(f"Error parsing a film entry: {e}")
    
    
    if TELEGRAM_BOT:
        if choices:
            bot.send_message(f"Lista dei risultati:", choices)

    # Return the number of titles found
    return media_search_manager.get_length()