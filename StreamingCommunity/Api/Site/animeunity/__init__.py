# 21.05.24

import sys
import subprocess


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.Api.Template import get_select_title
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance


# Logic class
from .site import title_search, media_search_manager, table_show_manager
from .film import download_film
from .serie import download_series


# Variable
indice = 1
_useFor = "Anime"
_priority = 0
_engineDownload = "mp4"
_deprecate = False

msg = Prompt()
console = Console()


def get_user_input(string_to_search: str = None):
    """
    Asks the user to input a search term.
    Handles both Telegram bot input and direct input.
    """
    if string_to_search is None:
        if site_constant.TELEGRAM_BOT:
            bot = get_bot_instance()
            string_to_search = bot.ask(
                "key_search",
                f"Enter the search term\nor type 'back' to return to the menu: ",
                None
            )

            if string_to_search == 'back':

                # Restart the script
                subprocess.Popen([sys.executable] + sys.argv)
                sys.exit()
        else:
            string_to_search = msg.ask(f"\n[purple]Insert a word to search in [green]{site_constant.SITE_NAME}").strip()

    return string_to_search

def process_search_result(select_title, selections=None):
    """
    Handles the search result and initiates the download for either a film or series.
    
    Parameters:
        select_title (MediaItem): The selected media item
        selections (dict, optional): Dictionary containing selection inputs that bypass manual input
                                    {'season': season_selection, 'episode': episode_selection}
    """
    if select_title.type == 'Movie' or select_title.type == 'OVA':
        download_film(select_title)

    else:
        season_selection = None
        episode_selection = None

        if selections:
            season_selection = selections.get('season')
            episode_selection = selections.get('episode')
            
        download_series(select_title, season_selection, episode_selection)

def search(string_to_search: str = None, get_onlyDatabase: bool = False, direct_item: dict = None, selections: dict = None):
    """
    Main function of the application for search.

    Parameters:
        string_to_search (str, optional): String to search for
        get_onlyDatabase (bool, optional): If True, return only the database object
        direct_item (dict, optional): Direct item to process (bypass search)
        selections (dict, optional): Dictionary containing selection inputs that bypass manual input
                                    {'season': season_selection, 'episode': episode_selection}
    """
    if direct_item:
        select_title = MediaItem(**direct_item)
        process_search_result(select_title, selections)
        return

    # Get the user input for the search term
    string_to_search = get_user_input(string_to_search)

    # Perform the database search
    len_database = title_search(string_to_search)

    # If only the database is needed, return the manager
    if get_onlyDatabase:
        return media_search_manager
    
    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()

    if len_database > 0:
        select_title = get_select_title(table_show_manager, media_search_manager,len_database)
        process_search_result(select_title, selections)
    
    else:
        console.print(f"\n[red]Nothing matching was found for[white]: [purple]{string_to_search}")

        if site_constant.TELEGRAM_BOT:
            bot.send_message(f"No results found, please try again", None)

        # If no results are found, ask again
        string_to_search = get_user_input()
        search(string_to_search, get_onlyDatabase, None, selections)