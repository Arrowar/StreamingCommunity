# 09.06.24

from urllib.parse import quote_plus


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
from .series import download_series


# Variable
indice = 4
_useFor = "Serie"
_priority = 0
_engineDownload = "hls"
_deprecate = False

msg = Prompt()
console = Console()


def process_search_result(select_title, selections=None):
    """
    Handles the search result and initiates the download for either a film or series.
    
    Parameters:
        select_title (MediaItem): The selected media item
        selections (dict, optional): Dictionary containing selection inputs that bypass manual input
                                    {'season': season_selection, 'episode': episode_selection}
    """
    if not select_title:
        if site_constant.TELEGRAM_BOT:
            bot = get_bot_instance()
            bot.send_message("No title selected or selection cancelled.", None)
        else:
            console.print("[yellow]No title selected or selection cancelled.")
        return
    
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
    bot = None
    if site_constant.TELEGRAM_BOT:
        try:
            from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance
            bot = get_bot_instance()
        except Exception:
            bot = None

    if direct_item:
        select_title = MediaItem(**direct_item)
        process_search_result(select_title, selections)
        return

    if string_to_search is None:
        actual_search_query = msg.ask(f"\n[purple]Insert word to search in [green]{site_constant.SITE_NAME}").strip()
    else:
        actual_search_query = string_to_search

    # Handle empty input
    if not actual_search_query:
        if bot:
            if actual_search_query is None:
                bot.send_message("Search term not provided or operation cancelled. Returning.", None)
        return

    # Search on database (preserve quote_plus usage)
    len_database = title_search(quote_plus(actual_search_query))

    # If only the database is needed, return the manager
    if get_onlyDatabase:
        return media_search_manager

    if len_database > 0:
        select_title = get_select_title(table_show_manager, media_search_manager, len_database)
        process_search_result(select_title, selections)
    else:
        if bot:
            bot.send_message(f"No results found for: '{actual_search_query}'", None)
        else:
            console.print(f"\n[red]Nothing matching was found for[white]: [purple]{actual_search_query}")
        return