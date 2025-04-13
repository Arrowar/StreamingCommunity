# 21.03.25

# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.Api.Template import get_select_title
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem


# Logic class
from .site import title_search, media_search_manager, table_show_manager
from .serie import download_series
from .film import download_film


# Variable
indice = 8
_useFor = "anime"
_priority = 0
_engineDownload = "mp4"

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
    if select_title.type == "TV":
        episode_selection = None
        if selections:
            episode_selection = selections.get('episode')
        download_series(select_title, episode_selection)

    else:
        download_film(select_title)

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
    if string_to_search is None:
        string_to_search = msg.ask(f"\n[purple]Insert a word to search in [green]{site_constant.SITE_NAME}").strip()

    # Perform the database search
    len_database = title_search(string_to_search)

    # If only the database is needed, return the manager
    if get_onlyDatabase:
        return media_search_manager

    if len_database > 0:
        select_title = get_select_title(table_show_manager, media_search_manager)
        process_search_result(select_title, selections)
    
    else:
        # If no results are found, ask again
        console.print(f"\n[red]Nothing matching was found for[white]: [purple]{string_to_search}")
        search()