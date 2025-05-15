# 21.05.24

import sys
import subprocess
from urllib.parse import quote_plus


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.Api.Template import get_select_title
from StreamingCommunity.Lib.Proxies.proxy import ProxyFinder
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance


# Logic class
from .site import title_search, table_show_manager, media_search_manager
from .film import download_film
from .series import download_series


# Variable
indice = 0
_useFor = "Film_&_Serie"
_priority = 0
_engineDownload = "hls"
_deprecate = False

msg = Prompt()
console = Console()


def get_user_input(string_to_search: str = None):
    """
    Asks the user to input a search term.
    Handles both Telegram bot input and direct input.
    """
    if string_to_search is not None:
        return string_to_search.strip()

    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()
        user_response = bot.ask(
            "key_search", # Tipo di richiesta
            "Enter the search term\nor type 'back' to return to the menu: ",
            None
        )

        if user_response is None:
            bot.send_message("Timeout: Nessun termine di ricerca inserito.", None)
            return None

        if user_response.lower() == 'back':
            bot.send_message("Ritorno al menu principale...", None)
            
            try:
                subprocess.Popen([sys.executable] + sys.argv)
                sys.exit()
                
            except Exception as e:
                bot.send_message(f"Errore durante il tentativo di riavvio: {e}", None)
                return None
        
        return user_response.strip()
        
    else:
        return msg.ask(f"\n[purple]Insert a word to search in [green]{site_constant.SITE_NAME}").strip()

def process_search_result(select_title, selections=None):
    """
    Handles the search result and initiates the download for either a film or series.
    
    Parameters:
        select_title (MediaItem): The selected media item. Può essere None se la selezione fallisce.
        selections (dict, optional): Dictionary containing selection inputs that bypass manual input
                                    {'season': season_selection, 'episode': episode_selection}
    """
    if not select_title:
        if site_constant.TELEGRAM_BOT:
            bot = get_bot_instance()
            bot.send_message("Nessun titolo selezionato o selezione annullata.", None)
        else:
            console.print("[yellow]Nessun titolo selezionato o selezione annullata.")
        return

    if select_title.type == 'tv':
        season_selection = None
        episode_selection = None
        
        if selections:
            season_selection = selections.get('season')
            episode_selection = selections.get('episode')

        download_series(select_title, season_selection, episode_selection)
        
    else:
        download_film(select_title)

def search(string_to_search: str = None, get_onlyDatabase: bool = False, direct_item: dict = None, selections: dict = None):
    """
    Main function of the application for search.

    Parameters:
        string_to_search (str, optional): String to search for. Può essere passato da run.py.
        get_onlyDatabase (bool, optional): If True, return only the database object.
        direct_item (dict, optional): Direct item to process (bypass search).
        selections (dict, optional): Dictionary containing selection inputs that bypass manual input.
    """
    bot = None
    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()

    if direct_item:
        select_title_obj = MediaItem(**direct_item)
        process_search_result(select_title_obj, selections)
        return

    actual_search_query = get_user_input(string_to_search)

    if not actual_search_query: # Se l'utente ha scritto 'back' (gestito da get_user_input) o input vuoto/timeout
        if bot:
             if actual_search_query is None:
                bot.send_message("Termine di ricerca non fornito. Ritorno al menu precedente.", None)
        return

    # title_search (da site.py) MOSTRA la lista dei risultati all'utente via bot.
    len_database = title_search(actual_search_query)

    if string_to_search == 'back':

        # Restart the script
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit()
    else:
        string_to_search = msg.ask(f"\n[purple]Insert a word to search in [green]{site_constant.SITE_NAME}").strip()

    # Search on database
    finder = ProxyFinder(site_constant.FULL_URL)
    proxy = finder.find_fast_proxy()
    len_database = title_search(string_to_search, proxy)

    # If only the database is needed, return the manager
    if get_onlyDatabase:
        return media_search_manager
    
    if len_database > 0:
        
        # Se ci sono risultati, chiama get_select_title per chiedere all'utente quale selezionare.
        select_title_obj = get_select_title(
            table_show_manager,
            media_search_manager,
            len_database
        )
        
        process_search_result(select_title_obj, selections)
    
    else:
        no_results_message = f"Nessun risultato trovato per: '{actual_search_query}'"
        if bot:
            bot.send_message(no_results_message, None)
        else:
            console.print(f"\n[red]Nothing matching was found for[white]: [purple]{actual_search_query}")
        
        # NON chiamare search() ricorsivamente.
        return
