# 09.06.24

import logging
from urllib.parse import quote_plus


# Internal utilities
from StreamingCommunity.Util.console import console, msg
from StreamingCommunity.Api.Template import get_select_title


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from .site import title_search, media_search_manager, table_show_manager
from .series import download_thread


# Variable
indice = 3
_useFor = "serie"
_deprecate = False
_priority = 2
_engineDownload = "mp4"


def search(string_to_search: str = None, get_onylDatabase: bool = False):
    """
    Main function of the application for film and series.
    """

    if string_to_search is None:
        string_to_search = msg.ask(f"\n[purple]Insert word to search in [green]{site_constant.SITE_NAME}").strip()
    
    # Search on database
    len_database = title_search(quote_plus(string_to_search))

    # Return list of elements
    if get_onylDatabase:
        return media_search_manager

    if len_database > 0:

        # Select title from list
        select_title = get_select_title(table_show_manager, media_search_manager)

        # Download only film
        if "Serie TV" in str(select_title.type):
            download_thread(select_title)

        else:
            logging.error(f"Not supported: {select_title.type}")

    else:
        console.print(f"\n[red]Nothing matching was found for[white]: [purple]{string_to_search}")

        # Retry
        search()