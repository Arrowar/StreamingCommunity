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
_useFor = "Film_&_Serie" # "Movies_&_Series"
_priority = 0
_engineDownload = "hls"
_deprecate = False

msg = Prompt()
console = Console()
proxy = None


def get_user_input(string_to_search: str = None):
    """
    Asks the user to input a search term.
    Handles both Telegram bot input and direct input.
    If string_to_search is provided, it's returned directly (after stripping).
    """
    if string_to_search is not None:
        return string_to_search.strip()

    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()
        user_response = bot.ask(
            "key_search", # Request type
            "Enter the search term\nor type 'back' to return to the menu: ",
            None
        )

        if user_response is None:
            bot.send_message("Timeout: No search term entered.", None)
            return None

        if user_response.lower() == 'back':
            bot.send_message("Returning to the main menu...", None)
            
            try:
                # Restart the script
                subprocess.Popen([sys.executable] + sys.argv)
                sys.exit()
                
            except Exception as e:
                bot.send_message(f"Error during restart attempt: {e}", None)
                return None # Return None if restart fails
        
        return user_response.strip()
        
    else:
        return msg.ask(f"\n[purple]Insert a word to search in [green]{site_constant.SITE_NAME}").strip()

def process_search_result(select_title, selections=None, proxy=None):
    """
    Handles the search result and initiates the download for either a film or series.
    
    Parameters:
        select_title (MediaItem): The selected media item. Can be None if selection fails.
        selections (dict, optional): Dictionary containing selection inputs that bypass manual input
                                    e.g., {'season': season_selection, 'episode': episode_selection}
        proxy (str, optional): The proxy to use for downloads.
    """
    if not select_title:
        if site_constant.TELEGRAM_BOT:
            bot = get_bot_instance()
            bot.send_message("No title selected or selection cancelled.", None)
        else:
            console.print("[yellow]No title selected or selection cancelled.")
        return

    if select_title.type == 'tv':
        season_selection = None
        episode_selection = None
        
        if selections:
            season_selection = selections.get('season')
            episode_selection = selections.get('episode')

        download_series(select_title, season_selection, episode_selection, proxy)
        
    else:
        download_film(select_title, proxy)

def search(string_to_search: str = None, get_onlyDatabase: bool = False, direct_item: dict = None, selections: dict = None):
    """
    Main function of the application for search.

    Parameters:
        string_to_search (str, optional): String to search for. Can be passed from run.py.
                                          If 'back', special handling might occur in get_user_input.
        get_onlyDatabase (bool, optional): If True, return only the database search manager object.
        direct_item (dict, optional): Direct item to process (bypasses search).
        selections (dict, optional): Dictionary containing selection inputs that bypass manual input
                                     for series (season/episode).
    """
    bot = None
    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()

    # Check proxy if not already set
    finder = ProxyFinder(site_constant.FULL_URL)
    proxy = finder.find_fast_proxy()
    
    if direct_item:
        select_title_obj = MediaItem(**direct_item)
        process_search_result(select_title_obj, selections, proxy)
        return
    


    actual_search_query = get_user_input(string_to_search)

    # Handle cases where user input is empty, or 'back' was handled (sys.exit or None return)
    if not actual_search_query: 
        if bot:
             if actual_search_query is None: # Specifically for timeout from bot.ask or failed restart
                bot.send_message("Search term not provided or operation cancelled. Returning.", None)
        return

    # Perform search on the database using the obtained query
    finder = ProxyFinder(site_constant.FULL_URL)
    proxy = finder.find_fast_proxy()
    len_database = title_search(actual_search_query, proxy)

    # If only the database object (media_search_manager populated by title_search) is needed
    if get_onlyDatabase:
        return media_search_manager 
    
    if len_database > 0:
        select_title = get_select_title(table_show_manager, media_search_manager, len_database)
        process_search_result(select_title, selections, proxy)
    
    else:
        no_results_message = f"No results found for: '{actual_search_query}'"
        if bot:
            bot.send_message(no_results_message, None)
        else:
            console.print(f"\n[red]Nothing matching was found for[white]: [purple]{actual_search_query}")
        
        # Do not call search() recursively here to avoid infinite loops on no results.
        # The flow should return to the caller (e.g., main menu in run.py).
        return